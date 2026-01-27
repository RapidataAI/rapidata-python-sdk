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

        # Split into batches
        batch_size = rapidata_config.upload.batchSize
        batches = [urls[i : i + batch_size] for i in range(0, len(urls), batch_size)]

        logger.info(f"Submitting {len(urls)} URLs in {len(batches)} batch(es)")

        # Submit all batches immediately (parallel)
        batch_ids = []
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
                # Fall back to individual uploads for this batch
                for url in batch:
                    failed_upload = FailedUpload(
                        item=url,
                        error_type="BatchSubmissionFailed",
                        error_message=f"Failed to submit batch: {str(e)}",
                    )
                    # Don't return early - try to submit remaining batches

        if not batch_ids:
            logger.error("No batches were successfully submitted")
            return [
                FailedUpload(
                    item=url,
                    error_type="BatchSubmissionFailed",
                    error_message="Failed to submit any batches",
                )
                for url in urls
            ]

        # Poll all batches together until complete
        logger.debug(f"Polling {len(batch_ids)} batch(es) for completion")
        last_completed = 0
        poll_interval = rapidata_config.upload.batchPollInterval
        start_time = time.time()

        while True:
            try:
                status = (
                    self.openapi_service.batch_upload_api.asset_batch_upload_status_get(
                        batch_upload_ids=batch_ids
                    )
                )

                # Update progress
                if progress_callback:
                    new_completed = status.completed_count + status.failed_count
                    if new_completed > last_completed:
                        progress_callback(new_completed - last_completed)
                        last_completed = new_completed

                # Check if all complete
                if status.status == BatchUploadStatus.COMPLETED:
                    logger.info(
                        f"All batches completed: {status.completed_count} succeeded, {status.failed_count} failed"
                    )
                    break

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > rapidata_config.upload.batchTimeout:
                    logger.error(
                        f"Batch upload timeout after {elapsed:.1f}s (limit: {rapidata_config.upload.batchTimeout}s)"
                    )
                    # Abort batches and return failures
                    for batch_id in batch_ids:
                        try:
                            self.openapi_service.batch_upload_api.asset_batch_upload_batch_upload_id_abort_post(
                                batch_upload_id=batch_id
                            )
                        except Exception as e:
                            logger.warning(f"Failed to abort batch {batch_id}: {e}")
                    return [
                        FailedUpload(
                            item=url,
                            error_type="BatchUploadTimeout",
                            error_message=f"Batch upload timed out after {elapsed:.1f}s",
                        )
                        for url in urls
                    ]

                # Exponential backoff with max interval
                time.sleep(poll_interval)
                poll_interval = min(
                    poll_interval * 1.5, rapidata_config.upload.batchPollMaxInterval
                )

            except Exception as e:
                logger.error(f"Error polling batch status: {e}")
                # Continue polling after error
                time.sleep(poll_interval)

        # Fetch results from each batch
        logger.debug(f"Fetching results from {len(batch_ids)} batch(es)")
        failed_uploads: list[FailedUpload[str]] = []
        successful_count = 0

        for batch_idx, batch_id in enumerate(batch_ids):
            try:
                result = self.openapi_service.batch_upload_api.asset_batch_upload_batch_upload_id_get(
                    batch_upload_id=batch_id
                )

                for item in result.items:
                    if item.status == BatchUploadUrlStatus.COMPLETED:
                        # Cache successful upload
                        cache_key = self._get_url_cache_key(item.url)
                        self.url_cache._storage[cache_key] = item.file_name
                        successful_count += 1
                        logger.debug(
                            f"Cached successful upload: {item.url} -> {item.file_name}"
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
                # Can't determine which URLs failed in this batch
                # Add generic error for the entire batch
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

    def _get_url_cache_key(self, url: str) -> str:
        """Generate cache key for a URL, including environment."""
        env = self.openapi_service.environment
        return f"{env}@{url}"
