from typing import TypeVar, Generic, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config.rapidata_config import rapidata_config
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload

from opentelemetry import context as otel_context

T = TypeVar("T")


class ThreadedUploader(Generic[T]):
    """
    A generic multi-threaded uploader that handles retries, progress tracking,
    and OpenTelemetry context propagation.

    Type Parameters:
        T: The type of items being uploaded.
    """

    def __init__(
        self,
        upload_fn: Callable[[T, int], None],
        description: str = "Uploading items",
    ):
        """
        Initialize the threaded uploader.

        Args:
            upload_fn: A function that uploads a single item. Takes (item, index) as arguments.
            description: Description shown in the progress bar.
        """
        self.upload_fn = upload_fn
        self.description = description

    def upload(self, items: list[T]) -> tuple[list[T], list[FailedUpload[T]]]:
        """
        Upload items in parallel using multiple threads.

        Args:
            items: List of items to upload.

        Returns:
            tuple[list[T], list[FailedUpload[T]]]: Lists of successful uploads and failed uploads with error details.
        """
        successful_uploads: list[T] = []
        failed_uploads: list[FailedUpload[T]] = []

        with tqdm(
            total=len(items),
            desc=self.description,
            disable=rapidata_config.logging.silent_mode,
        ) as progress_bar:

            def process_upload_with_context(
                context: otel_context.Context, item: T, index: int
            ) -> tuple[list[T], list[FailedUpload[T]]]:
                """Wrapper function that runs upload with the provided context."""
                token = otel_context.attach(context)
                try:
                    return self._process_single_upload(item, index)
                finally:
                    otel_context.detach(token)

            # Capture the current OpenTelemetry context before creating threads
            current_context = otel_context.get_current()

            with ThreadPoolExecutor(
                max_workers=rapidata_config.upload.maxWorkers
            ) as executor:
                futures = [
                    executor.submit(
                        process_upload_with_context,
                        current_context,
                        item,
                        i,
                    )
                    for i, item in enumerate(items)
                ]

                for future in as_completed(futures):
                    try:
                        chunk_successful, chunk_failed = future.result()
                        successful_uploads.extend(chunk_successful)
                        failed_uploads.extend(chunk_failed)
                        progress_bar.update(len(chunk_successful) + len(chunk_failed))
                    except Exception as e:
                        logger.error("Future execution failed: %s", str(e))

        if failed_uploads:
            logger.error(
                "Upload failed for %s items: %s",
                len(failed_uploads),
                failed_uploads,
            )

        return successful_uploads, failed_uploads

    def _process_single_upload(
        self,
        item: T,
        index: int,
    ) -> tuple[list[T], list[FailedUpload[T]]]:
        """
        Process single upload with retry logic and error tracking.

        Args:
            item: Item to upload.
            index: Sort index for the upload.

        Returns:
            tuple[list[T], list[FailedUpload[T]]]: Lists of successful items and failed items with error details.
        """
        logger.debug("Processing single upload for %s with index %s", item, index)

        local_successful: list[T] = []
        local_failed: list[FailedUpload[T]] = []

        last_exception = None
        for attempt in range(rapidata_config.upload.maxRetries):
            try:
                from rapidata.rapidata_client.api.rapidata_api_client import (
                    suppress_rapidata_error_logging,
                )

                with suppress_rapidata_error_logging():
                    self.upload_fn(item, index)

                local_successful.append(item)
                return local_successful, local_failed

            except Exception as e:
                last_exception = e
                if attempt < rapidata_config.upload.maxRetries - 1:
                    # Exponential backoff: wait 1s, then 2s, then 4s
                    retry_delay = 2**attempt
                    time.sleep(retry_delay)
                    logger.debug("Error: %s", str(last_exception))
                    logger.debug(
                        "Retrying %s of %s...",
                        attempt + 1,
                        rapidata_config.upload.maxRetries,
                    )

        # If we get here, all retries failed
        failed_upload = FailedUpload.from_exception(item, last_exception)
        local_failed.append(failed_upload)
        tqdm.write(
            f"Upload failed for {item} after {rapidata_config.upload.maxRetries} attempts. \nFinal error ({failed_upload.error_type}): \n{failed_upload.error_message}"
        )

        return local_successful, local_failed
