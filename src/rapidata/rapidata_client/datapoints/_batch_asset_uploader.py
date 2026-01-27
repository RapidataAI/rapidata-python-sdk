from __future__ import annotations

import time
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

    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.url_cache = AssetUploader._url_cache

    def batch_upload_urls(
        self,
        urls: list[str],
        progress_callback: Callable[[int], None] | None = None,
    ) -> list[FailedUpload[str]]:
        """
        Upload URLs in batches. Returns list of failed uploads.
        Successful uploads are cached automatically.

        Args:
            urls: List of URLs to upload.
            progress_callback: Optional callback to report progress (called with number of newly completed items).

        Returns:
            List of FailedUpload instances for any URLs that failed.
        """
        if not urls:
            return []

        # Split and submit batches
        batches = self._split_into_batches(urls)
        batch_ids = self._submit_batches(batches)

        if not batch_ids:
            logger.error("No batches were successfully submitted")
            return self._create_submission_failures(urls)

        # Poll until complete
        self._poll_until_complete(batch_ids, progress_callback)

        # Fetch and process results
        return self._fetch_and_process_results(batch_ids)

    def _split_into_batches(self, urls: list[str]) -> list[list[str]]:
        """Split URLs into batches of configured size."""
        batch_size = rapidata_config.upload.batchSize
        batches = [urls[i : i + batch_size] for i in range(0, len(urls), batch_size)]
        logger.info(f"Submitting {len(urls)} URLs in {len(batches)} batch(es)")
        return batches

    def _submit_batches(self, batches: list[list[str]]) -> list[str]:
        """
        Submit all batches to the API.

        Args:
            batches: List of URL batches to submit.

        Returns:
            List of batch IDs that were successfully submitted.
        """
        batch_ids: list[str] = []

        for batch_idx, batch in enumerate(batches):
            try:
                result = self.openapi_service.batch_upload_api.asset_batch_upload_post(
                    create_batch_upload_endpoint_input=CreateBatchUploadEndpointInput(
                        urls=batch
                    )
                )
                batch_ids.append(result.batch_upload_id)
                logger.debug(
                    f"Submitted batch {batch_idx + 1}/{len(batches)}: {result.batch_upload_id}"
                )
            except Exception as e:
                logger.error(f"Failed to submit batch {batch_idx + 1}: {e}")
                # Continue trying to submit remaining batches

        logger.info(f"Successfully submitted {len(batch_ids)}/{len(batches)} batches")
        return batch_ids

    def _poll_until_complete(
        self,
        batch_ids: list[str],
        progress_callback: Callable[[int], None] | None,
    ) -> None:
        """
        Poll batches until all complete.

        Args:
            batch_ids: List of batch IDs to poll.
            progress_callback: Optional callback to report progress.
        """
        logger.debug(f"Polling {len(batch_ids)} batch(es) for completion")

        # Scale initial polling interval based on batch count
        # More batches = longer expected completion time = less frequent polling
        poll_interval = rapidata_config.upload.batchPollInterval

        last_completed = 0
        start_time = time.time()

        while True:
            try:
                status = (
                    self.openapi_service.batch_upload_api.asset_batch_upload_status_get(
                        batch_upload_ids=batch_ids
                    )
                )

                # Update progress
                self._update_progress(status, last_completed, progress_callback)
                last_completed = status.completed_count + status.failed_count

                # Check completion
                if status.status == BatchUploadStatus.COMPLETED:
                    elapsed = time.time() - start_time
                    logger.info(
                        f"All batches completed in {elapsed:.1f}s: "
                        f"{status.completed_count} succeeded, {status.failed_count} failed"
                    )
                    return

                # Wait before next poll (exponential backoff)
                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling batch status: {e}")
                time.sleep(poll_interval)

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

    def _fetch_and_process_results(
        self, batch_ids: list[str]
    ) -> list[FailedUpload[str]]:
        """
        Fetch results from all batches and process them.

        Args:
            batch_ids: List of batch IDs to fetch results from.

        Returns:
            List of failed uploads.
        """
        logger.debug(f"Fetching results from {len(batch_ids)} batch(es)")
        failed_uploads: list[FailedUpload[str]] = []
        successful_count = 0

        for batch_idx, batch_id in enumerate(batch_ids):
            try:
                result = self.openapi_service.batch_upload_api.asset_batch_upload_batch_upload_id_get(
                    batch_upload_id=batch_id
                )

                # Process each URL in the batch result
                for item in result.items:
                    if item.status == BatchUploadUrlStatus.COMPLETED:
                        # Cache successful upload using proper API
                        if item.file_name is not None:
                            cache_key = self._get_url_cache_key(item.url)
                            self.url_cache.set(cache_key, item.file_name)
                            successful_count += 1
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
                failed_uploads.append(
                    FailedUpload(
                        item=f"batch_{batch_idx}",
                        error_type="BatchResultFetchFailed",
                        error_message=f"Failed to fetch batch results: {str(e)}",
                    )
                )

        logger.info(
            f"Batch upload complete: {successful_count} succeeded, {len(failed_uploads)} failed"
        )
        return failed_uploads

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

    def _get_url_cache_key(self, url: str) -> str:
        """Generate cache key for a URL, including environment."""
        env = self.openapi_service.environment
        return f"{env}@{url}"
