from __future__ import annotations

import time
import threading
from typing import Callable, TYPE_CHECKING

from rapidata.rapidata_client.config import logger, rapidata_config
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.api_client.models.batch_upload_status import BatchUploadStatus
from rapidata.api_client.models.batch_upload_url_status import BatchUploadUrlStatus
from rapidata.api_client.models.create_batch_upload_endpoint_input import (
    CreateBatchUploadEndpointInput,
)

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.api_client.models.get_batch_upload_status_endpoint_output import (
        GetBatchUploadStatusEndpointOutput,
    )


class BatchAssetUploader:
    """
    Handles batch uploading of URL assets using the batch upload API.

    This class submits URLs in batches, polls for completion, and updates
    the shared URL cache with successful uploads.
    """

    def __init__(self, openapi_service: OpenAPIService) -> None:
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)
        self.url_cache = AssetUploader._url_cache
        self._interrupted = False

    def batch_upload_urls(
        self,
        urls: list[str],
        progress_callback: Callable[[int], None] | None = None,
        completion_callback: Callable[[list[str]], None] | None = None,
    ) -> list[FailedUpload[str]]:
        """
        Upload URLs in batches. Returns list of failed uploads.
        Successful uploads are cached automatically.

        Batches are submitted concurrently with polling - polling starts as soon
        as the first batch is submitted, allowing progress to be visible immediately.

        Args:
            urls: List of URLs to upload.
            progress_callback: Optional callback to report progress (called with number of newly completed items).
            completion_callback: Optional callback to notify when URLs complete (called with list of successful URLs).

        Returns:
            List of FailedUpload instances for any URLs that failed.
        """
        if not urls:
            return []

        # Split into batches
        batches = self._split_into_batches(urls)

        # Thread-safe collections for concurrent submission and polling
        batch_ids_lock = threading.Lock()
        batch_ids: list[str] = []
        batch_to_urls: dict[str, list[str]] = {}
        submission_complete = threading.Event()

        try:
            # Submit batches in background thread
            def submit_batches_background():
                """Submit all batches and signal completion."""
                for batch_idx, batch in enumerate(batches):
                    # Check if interrupted before submitting next batch
                    if self._interrupted:
                        logger.debug("Batch submission stopped due to interruption")
                        break

                    try:
                        result = self.openapi_service.batch_upload_api.asset_batch_upload_post(
                            create_batch_upload_endpoint_input=CreateBatchUploadEndpointInput(
                                urls=batch
                            )
                        )
                        batch_id = result.batch_upload_id

                        # Add to shared collections (thread-safe)
                        with batch_ids_lock:
                            batch_ids.append(batch_id)
                            batch_to_urls[batch_id] = batch

                        logger.debug(
                            f"Submitted batch {batch_idx + 1}/{len(batches)}: {batch_id}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to submit batch {batch_idx + 1}: {e}")

                # Signal that all batches have been submitted
                submission_complete.set()
                with batch_ids_lock:
                    logger.info(
                        f"Successfully submitted {len(batch_ids)}/{len(batches)} batches"
                    )

            # Start background submission
            submission_thread = threading.Thread(
                target=submit_batches_background, daemon=True
            )
            submission_thread.start()

            # Wait for at least one batch to be submitted before starting poll
            while len(batch_ids) == 0 and not submission_complete.is_set():
                time.sleep(0.5)

            if len(batch_ids) == 0:
                logger.error("No batches were successfully submitted")
                return self._create_submission_failures(urls)

            # Poll until complete (will handle dynamically growing batch list)
            return self._poll_until_complete(
                batch_ids,
                batch_to_urls,
                batch_ids_lock,
                submission_complete,
                progress_callback,
                completion_callback,
            )

        except KeyboardInterrupt:
            logger.warning("Batch upload interrupted by user (Ctrl+C)")
            self._interrupted = True
            raise  # Re-raise to propagate interruption

        finally:
            # Cleanup: abort batches if interrupted
            if self._interrupted:
                self._abort_batches(batch_ids, batch_ids_lock)

    def _split_into_batches(self, urls: list[str]) -> list[list[str]]:
        """Split URLs into batches of configured size."""
        batch_size = rapidata_config.upload.batchSize
        batches = [urls[i : i + batch_size] for i in range(0, len(urls), batch_size)]
        logger.info(f"Submitting {len(urls)} URLs in {len(batches)} batch(es)")
        return batches

    def _poll_until_complete(
        self,
        batch_ids: list[str],
        batch_to_urls: dict[str, list[str]],
        batch_ids_lock: threading.Lock,
        submission_complete: threading.Event,
        progress_callback: Callable[[int], None] | None,
        completion_callback: Callable[[list[str]], None] | None,
    ) -> list[FailedUpload[str]]:
        """
        Poll batches until all complete. Process batches incrementally as they complete.

        Supports concurrent batch submission - will poll currently submitted batches
        and continue until all batches are submitted and completed.

        Args:
            batch_ids: Shared list of batch IDs (grows as batches are submitted).
            batch_to_urls: Shared mapping from batch_id to list of URLs in that batch.
            batch_ids_lock: Lock protecting batch_ids and batch_to_urls.
            submission_complete: Event signaling all batches have been submitted.
            progress_callback: Optional callback to report progress.
            completion_callback: Optional callback to notify when URLs complete.

        Returns:
            List of FailedUpload instances for any URLs that failed.
        """
        poll_interval = rapidata_config.upload.batchPollInterval

        last_completed = 0
        start_time = time.time()
        processed_batches: set[str] = set()
        all_failures: list[FailedUpload[str]] = []

        while True:
            # Check for interruption at start of each iteration
            if self._interrupted:
                logger.debug("Polling stopped due to interruption")
                break

            # Get current batch IDs (thread-safe)
            with batch_ids_lock:
                current_batch_ids = batch_ids.copy()
                total_batches_submitted = len(current_batch_ids)

            if not current_batch_ids:
                # No batches yet, wait a bit
                time.sleep(poll_interval)
                continue

            logger.debug(
                f"Polling {total_batches_submitted} submitted batch(es) for completion"
            )
            try:
                status = (
                    self.openapi_service.batch_upload_api.asset_batch_upload_status_get(
                        batch_upload_ids=current_batch_ids
                    )
                )

                # Process newly completed batches
                for batch_id in status.completed_batches:
                    if batch_id not in processed_batches:
                        successful_urls, failures = self._process_single_batch(
                            batch_id, batch_to_urls
                        )
                        processed_batches.add(batch_id)
                        all_failures.extend(failures)

                        # Notify callback with completed URLs
                        if completion_callback and successful_urls:
                            completion_callback(successful_urls)

                # Update progress
                self._update_progress(status, last_completed, progress_callback)
                last_completed = status.completed_count + status.failed_count

                # Check if we're done:
                # 1. All batches have been submitted
                # 2. All submitted batches have been processed
                if submission_complete.is_set() and len(processed_batches) == len(
                    current_batch_ids
                ):
                    elapsed = time.time() - start_time
                    logger.info(
                        f"All batches completed in {elapsed:.1f}s: "
                        f"{status.completed_count} succeeded, {status.failed_count} failed"
                    )
                    return all_failures

                # Wait before next poll
                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling batch status: {e}")
                time.sleep(poll_interval)

        # Return failures collected so far (reached via break on interruption)
        return all_failures

    def _update_progress(
        self,
        status: GetBatchUploadStatusEndpointOutput,
        last_completed: int,
        progress_callback: Callable[[int], None] | None,
    ) -> None:
        """Update progress callback if provided."""
        if progress_callback:
            new_completed = status.completed_count + status.failed_count
            if new_completed > last_completed:
                progress_callback(new_completed - last_completed)

    def _process_single_batch(
        self, batch_id: str, batch_to_urls: dict[str, list[str]]
    ) -> tuple[list[str], list[FailedUpload[str]]]:
        """
        Fetch and cache results for a single batch.

        Args:
            batch_id: The batch ID to process.
            batch_to_urls: Mapping from batch_id to list of URLs in that batch.

        Returns:
            Tuple of (successful_urls, failed_uploads).
        """
        successful_urls: list[str] = []
        failed_uploads: list[FailedUpload[str]] = []

        try:
            result = self.openapi_service.batch_upload_api.asset_batch_upload_batch_upload_id_get(
                batch_upload_id=batch_id
            )

            # Process each URL in the batch result
            for item in result.items:
                if item.status == BatchUploadUrlStatus.COMPLETED:
                    # Cache successful upload using proper API
                    if item.file_name is not None:
                        cache_key = self.asset_uploader.get_url_cache_key(item.url)
                        self.url_cache.set(cache_key, item.file_name)
                        successful_urls.append(item.url)
                        logger.debug(
                            f"Cached successful upload: {item.url} -> {item.file_name}"
                        )
                    else:
                        logger.warning(
                            f"Batch upload completed but file_name is None for URL: {item.url}"
                        )
                        failed_uploads.append(
                            FailedUpload(
                                item=item.url,
                                error_type="BatchUploadFailed",
                                error_message="Upload completed but file_name is None",
                            )
                        )
                else:
                    # Track failure
                    failed_uploads.append(
                        FailedUpload(
                            item=item.url,
                            error_type="BatchUploadFailed",
                            error_message=item.error_message
                            or "Unknown batch upload error",
                        )
                    )
                    logger.warning(
                        f"URL failed in batch: {item.url} - {item.error_message}"
                    )

        except Exception as e:
            logger.error(f"Failed to fetch results for batch {batch_id}: {e}")
            # Create individual FailedUpload for each URL in the failed batch
            # Use from_exception to extract proper error reason from RapidataError
            if batch_id in batch_to_urls:
                for url in batch_to_urls[batch_id]:
                    failed_uploads.append(FailedUpload.from_exception(url, e))
            else:
                # Fallback if batch_id not found in mapping
                failed_uploads.append(
                    FailedUpload.from_exception(f"batch_{batch_id}", e)
                )

        if successful_urls:
            logger.debug(
                f"Batch {batch_id}: {len(successful_urls)} succeeded, {len(failed_uploads)} failed"
            )

        return successful_urls, failed_uploads

    def _create_submission_failures(self, urls: list[str]) -> list[FailedUpload[str]]:
        """Create FailedUpload instances for all URLs when submission fails."""
        return [
            FailedUpload(
                item=url,
                error_type="BatchSubmissionFailed",
                error_message="Failed to submit any batches",
            )
            for url in urls
        ]

    def _abort_batches(
        self,
        batch_ids: list[str],
        batch_ids_lock: threading.Lock,
    ) -> None:
        """
        Abort all submitted batches by calling the abort endpoint.

        This method is called during cleanup when the upload process is interrupted.
        It attempts to abort all batches that were successfully submitted.

        Args:
            batch_ids: Shared list of batch IDs (thread-safe access required).
            batch_ids_lock: Lock protecting batch_ids list.
        """
        # Get snapshot of current batch IDs
        with batch_ids_lock:
            batches_to_abort = batch_ids.copy()

        if not batches_to_abort:
            logger.info("No batches to abort")
            return

        logger.info(
            f"Aborting {len(batches_to_abort)} batch(es) due to interruption..."
        )

        abort_successes = 0
        abort_failures = 0

        for batch_id in batches_to_abort:
            try:
                self.openapi_service.batch_upload_api.asset_batch_upload_batch_upload_id_abort_post(
                    batch_upload_id=batch_id
                )
                abort_successes += 1
                logger.debug(f"Successfully aborted batch: {batch_id}")
            except Exception as e:
                abort_failures += 1
                logger.warning(f"Failed to abort batch {batch_id}: {e}")

        logger.info(
            f"Batch abort completed: {abort_successes} succeeded, {abort_failures} failed"
        )
