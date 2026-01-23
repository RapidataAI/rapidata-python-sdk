from typing import TypeVar, Generic, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config.rapidata_config import rapidata_config

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
        environment: Optional[str] = None,
    ):
        """
        Initialize the threaded uploader.

        Args:
            upload_fn: A function that uploads a single item. Takes (item, index) as arguments.
            description: Description shown in the progress bar.
            environment: Optional environment name for per-environment config persistence.
        """
        self.upload_fn = upload_fn
        self.description = description
        self.environment = environment or "production"

    def upload(self, items: list[T]) -> tuple[list[T], list[T]]:
        """
        Upload items in parallel using multiple threads.

        Args:
            items: List of items to upload.

        Returns:
            tuple[list[T], list[T]]: Lists of successful and failed uploads.
        """
        if not rapidata_config.upload.enableDynamicWorkers:
            # Static mode: Original behavior (backward compatibility)
            return self._upload_static(items)
        else:
            # Dynamic mode with smart batching (DEFAULT)
            return self._upload_with_dynamic_adjustment(items)

    def _upload_static(self, items: list[T]) -> tuple[list[T], list[T]]:
        """Original static upload implementation for backward compatibility."""
        successful_uploads: list[T] = []
        failed_uploads: list[T] = []

        with tqdm(
            total=len(items),
            desc=self.description,
            disable=rapidata_config.logging.silent_mode,
        ) as progress_bar:

            # Capture the current OpenTelemetry context before creating threads
            current_context = otel_context.get_current()

            with ThreadPoolExecutor(
                max_workers=rapidata_config.upload.maxWorkers
            ) as executor:
                futures = [
                    executor.submit(
                        self._process_upload_with_context,
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

    def _upload_with_dynamic_adjustment(
        self, items: list[T]
    ) -> tuple[list[T], list[T]]:
        """
        Upload with dynamic worker adjustment using smart batching.

        Processes items in configurable batches (default 1000), adjusting worker
        count between batches based on performance. Persists learned configuration.
        """
        from rapidata.rapidata_client.utils.dynamic_worker_controller import (
            DynamicWorkerController,
        )
        from rapidata.rapidata_client.utils.performance_monitor import (
            PerformanceMonitor,
        )

        # Initialize controller (loads from disk if available)
        controller = DynamicWorkerController(
            config=rapidata_config.upload, environment=self.environment
        )
        current_workers = controller.get_initial_workers()

        successful = []
        failed = []
        remaining = items.copy()

        with tqdm(
            total=len(items),
            desc=self.description,
            disable=rapidata_config.logging.silent_mode,
        ) as pbar:

            # Capture OpenTelemetry context for thread propagation
            current_context = otel_context.get_current()

            # Process in batches until all items uploaded
            while remaining:
                # Determine batch size (config default: 1000)
                batch_size = min(
                    len(remaining),
                    rapidata_config.upload.batchSize,
                    current_workers * 50,  # Cap: 50 items per worker
                )
                batch_size = max(batch_size, 10)  # Minimum batch size
                batch = remaining[:batch_size]
                remaining = remaining[batch_size:]

                # Create monitor for this batch
                batch_monitor = PerformanceMonitor(len(batch))

                logger.debug(
                    "Processing batch of %d items with %d workers",
                    len(batch),
                    current_workers,
                )

                # Upload batch with current worker count
                with ThreadPoolExecutor(max_workers=current_workers) as executor:
                    futures = [
                        executor.submit(
                            self._process_upload_with_context,
                            current_context,
                            item,
                            i,
                        )
                        for i, item in enumerate(
                            batch, start=len(successful) + len(failed)
                        )
                    ]

                    # Collect results as they complete
                    for future in as_completed(futures):
                        try:
                            chunk_successful, chunk_failed = future.result()

                            # Track results
                            successful.extend(chunk_successful)
                            failed.extend(chunk_failed)

                            # Update monitoring
                            for _ in chunk_successful:
                                batch_monitor.record_completion(success=True)
                            for _ in chunk_failed:
                                batch_monitor.record_completion(success=False)

                            # Update progress bar
                            pbar.update(len(chunk_successful) + len(chunk_failed))

                        except Exception as e:
                            logger.error("Future execution failed: %s", e)
                            batch_monitor.record_completion(success=False)

                # Batch complete - finalize metrics
                batch_monitor.finish_batch()

                # Log batch performance
                logger.info(
                    "Batch complete: %.1f items/sec, %.1f%% error rate, %.1fs duration",
                    batch_monitor.get_throughput(),
                    batch_monitor.get_error_rate() * 100,
                    batch_monitor.get_duration(),
                )

                # Record batch results with controller
                controller.record_batch_complete(batch_monitor)

                # Adjust workers for next batch (if we have more items)
                if remaining:
                    new_workers, reason = controller.calculate_adjustment(
                        batch_monitor
                    )

                    if new_workers != current_workers:
                        logger.info(
                            "Worker adjustment: %d → %d. Reason: %s",
                            current_workers,
                            new_workers,
                            reason,
                        )
                        current_workers = new_workers
                    else:
                        logger.debug("Workers unchanged (%d): %s", current_workers, reason)

        # Upload complete - save learned configuration
        controller.finalize_upload()

        # Log final summary
        if failed:
            logger.error("Upload failed for %d items: %s", len(failed), failed)

        logger.info(
            "Upload complete: %d successful, %d failed. Final worker count: %d",
            len(successful),
            len(failed),
            current_workers,
        )

        return successful, failed

    def _process_upload_with_context(
        self, context: otel_context.Context, item: T, index: int
    ) -> tuple[list[T], list[T]]:
        """Wrapper function that runs upload with the provided context."""
        token = otel_context.attach(context)
        try:
            return self._process_single_upload(item, index)
        finally:
            otel_context.detach(token)

    def _process_single_upload(
        self,
        item: T,
        index: int,
    ) -> tuple[list[T], list[T]]:
        """
        Process single upload with retry logic and error tracking.

        Args:
            item: Item to upload.
            index: Sort index for the upload.

        Returns:
            tuple[list[T], list[T]]: Lists of successful and failed items.
        """
        logger.debug("Processing single upload for %s with index %s", item, index)

        local_successful: list[T] = []
        local_failed: list[T] = []

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
        local_failed.append(item)
        tqdm.write(
            f"Upload failed for {item} after {rapidata_config.upload.maxRetries} attempts. \nFinal error: \n{str(last_exception)}"
        )

        return local_successful, local_failed
