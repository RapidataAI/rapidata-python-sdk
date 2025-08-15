from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.datapoints.assets import TextAsset, MediaAsset
from rapidata.service import LocalFileService
from rapidata.service.openapi_service import OpenAPIService
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from typing import Generator
from rapidata.rapidata_client.config import logger, managed_print
import time
import threading
from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)
from rapidata.rapidata_client.config.rapidata_config import rapidata_config

# Add OpenTelemetry context imports for thread propagation
from opentelemetry import context as otel_context


def chunk_list(lst: list, chunk_size: int) -> Generator:
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


class RapidataDataset:
    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.id = dataset_id
        self.openapi_service = openapi_service
        self.local_file_service = LocalFileService()

    def add_datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        if not datapoints:
            return [], []

        effective_asset_type = datapoints[0]._get_effective_asset_type()

        logger.debug(f"Config for datapoint upload: {rapidata_config}")

        if issubclass(effective_asset_type, MediaAsset):
            return self._add_media_from_paths(
                datapoints,
            )
        elif issubclass(effective_asset_type, TextAsset):
            return self._add_texts(datapoints)
        else:
            raise ValueError(f"Unsupported asset type: {effective_asset_type}")

    def _add_texts(
        self, datapoints: list[Datapoint]
    ) -> tuple[list[Datapoint], list[Datapoint]]:

        def upload_text_datapoint(datapoint: Datapoint, index: int) -> Datapoint:
            model = datapoint.create_text_upload_model(index)

            self.openapi_service.dataset_api.dataset_dataset_id_datapoints_texts_post(
                dataset_id=self.id, create_datapoint_from_text_sources_model=model
            )
            return datapoint

        def upload_with_context(
            context: otel_context.Context, datapoint: Datapoint, index: int
        ) -> Datapoint:
            """Wrapper function that runs upload_text_datapoint with the provided context."""
            token = otel_context.attach(context)
            try:
                return upload_text_datapoint(datapoint, index)
            finally:
                otel_context.detach(token)

        successful_uploads: list[Datapoint] = []
        failed_uploads: list[Datapoint] = []

        # Capture the current OpenTelemetry context before creating threads
        current_context = otel_context.get_current()

        total_uploads = len(datapoints)
        with ThreadPoolExecutor(
            max_workers=rapidata_config.upload.maxWorkers
        ) as executor:
            future_to_datapoint = {
                executor.submit(
                    upload_with_context, current_context, datapoint, i
                ): datapoint
                for i, datapoint in enumerate(datapoints)
            }

            with tqdm(
                total=total_uploads,
                desc="Uploading text datapoints",
                disable=rapidata_config.logging.silent_mode,
            ) as pbar:
                for future in as_completed(future_to_datapoint.keys()):
                    datapoint = future_to_datapoint[future]
                    try:
                        result = future.result()
                        pbar.update(1)
                        successful_uploads.append(result)
                    except Exception as e:
                        failed_uploads.append(datapoint)
                        logger.error("Upload failed for %s: %s", datapoint, str(e))

        return successful_uploads, failed_uploads

    def _process_single_upload(
        self,
        datapoint: Datapoint,
        index: int,
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        """
        Process single upload with retry logic and error tracking.

        Args:
            media_asset: MediaAsset or MultiAsset to upload
            meta_list: Optional sequence of metadata for the asset
            index: Sort index for the upload
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            tuple[list[Datapoint], list[Datapoint]]: Lists of successful and failed datapoints
        """
        logger.debug("Processing single upload for %s with index %s", datapoint, index)

        local_successful: list[Datapoint] = []
        local_failed: list[Datapoint] = []

        metadata = datapoint.get_prepared_metadata()

        local_paths = datapoint.get_local_file_paths()
        urls = datapoint.get_urls()

        last_exception = None
        for attempt in range(rapidata_config.upload.maxRetries):
            try:
                with suppress_rapidata_error_logging():
                    self.openapi_service.dataset_api.dataset_dataset_id_datapoints_post(
                        dataset_id=self.id,
                        file=local_paths,
                        url=urls,
                        metadata=metadata,
                        sort_index=index,
                    )

                local_successful.append(datapoint)

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
        local_failed.append(datapoint)
        tqdm.write(
            f"Upload failed for {datapoint} after {rapidata_config.upload.maxRetries} attempts. \nFinal error: \n{str(last_exception)}"
        )

        return local_successful, local_failed

    def _get_progress_tracker(
        self,
        total_uploads: int,
        stop_event: threading.Event,
        progress_error_event: threading.Event,
        progress_poll_interval: float,
    ) -> threading.Thread:
        """
        Create and return a progress tracking thread that shows actual API progress.

        Args:
            total_uploads: Total number of uploads to track
            initial_ready: Initial number of ready items
            initial_progress: Initial progress state
            stop_event: Event to signal thread to stop
            progress_error_event: Event to signal an error in progress tracking
            progress_poll_interval: Time between progress checks

        Returns:
            threading.Thread: The progress tracking thread
        """

        def progress_tracking_thread():
            try:
                # Initialize progress bar with 0 completions
                with tqdm(
                    total=total_uploads,
                    desc="Uploading datapoints",
                    disable=rapidata_config.logging.silent_mode,
                ) as pbar:
                    prev_ready = 0
                    prev_failed = 0
                    stall_count = 0
                    last_progress_time = time.time()

                    # We'll wait for all uploads to finish + some extra time
                    # for the backend to fully process everything
                    all_uploads_complete = threading.Event()

                    while not stop_event.is_set() or not all_uploads_complete.is_set():
                        try:
                            current_progress = self.openapi_service.dataset_api.dataset_dataset_id_progress_get(
                                self.id
                            )

                            # Calculate items completed since our initialization
                            completed_ready = current_progress.ready
                            completed_failed = current_progress.failed
                            total_completed = completed_ready + completed_failed

                            # Calculate newly completed items since our last check
                            new_ready = current_progress.ready - prev_ready
                            new_failed = current_progress.failed - prev_failed

                            # Update progress bar position to show actual completed items
                            # First reset to match the actual completed count
                            pbar.n = total_completed
                            pbar.refresh()

                            if new_ready > 0 or new_failed > 0:
                                # We saw progress
                                stall_count = 0
                                last_progress_time = time.time()
                            else:
                                stall_count += 1

                            # Update our tracking variables
                            prev_ready = current_progress.ready
                            prev_failed = current_progress.failed or 0

                            # Check if stop_event was set (all uploads submitted)
                            if stop_event.is_set():
                                elapsed_since_last_progress = (
                                    time.time() - last_progress_time
                                )

                                # If we haven't seen progress for a while after all uploads were submitted
                                if elapsed_since_last_progress > 5.0:
                                    # If we're at 100%, we're done
                                    if total_completed >= total_uploads:
                                        all_uploads_complete.set()
                                        break

                                    # If we're not at 100% but it's been a while with no progress
                                    if stall_count > 5:
                                        # We've polled several times with no progress, assume we're done
                                        logger.warning(
                                            "\nProgress seems stalled at %s/%s.",
                                            total_completed,
                                            total_uploads,
                                        )
                                        break

                        except Exception as e:
                            logger.error("\nError checking progress: %s", str(e))
                            stall_count += 1

                            if stall_count > 10:  # Too many consecutive errors
                                progress_error_event.set()
                                break

                        # Sleep before next poll
                        time.sleep(progress_poll_interval)

            except Exception as e:
                logger.error("Progress tracking thread error: %s", str(e))
                progress_error_event.set()

        # Create and return the thread
        progress_thread = threading.Thread(target=progress_tracking_thread)
        progress_thread.daemon = True
        return progress_thread

    def _process_uploads_in_chunks(
        self,
        datapoints: list[Datapoint],
        chunk_size: int,
        stop_progress_tracking: threading.Event,
        progress_tracking_error: threading.Event,
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        """
        Process uploads in chunks with a ThreadPoolExecutor.

        Args:
            media_paths: List of assets to upload
            multi_metadata: Optional sequence of sequences of metadata
            chunk_size: Number of items to process in each batch
            stop_progress_tracking: Event to signal progress tracking to stop
            progress_tracking_error: Event to detect progress tracking errors

        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed uploads
        """
        successful_uploads: list[Datapoint] = []
        failed_uploads: list[Datapoint] = []

        def process_upload_with_context(
            context: otel_context.Context, datapoint: Datapoint, index: int
        ) -> tuple[list[Datapoint], list[Datapoint]]:
            """Wrapper function that runs _process_single_upload with the provided context."""
            token = otel_context.attach(context)
            try:
                return self._process_single_upload(datapoint, index)
            finally:
                otel_context.detach(token)

        # Capture the current OpenTelemetry context before creating threads
        current_context = otel_context.get_current()

        try:
            with ThreadPoolExecutor(
                max_workers=rapidata_config.upload.maxWorkers
            ) as executor:
                # Process uploads in chunks to avoid overwhelming the system
                for chunk_idx, chunk in enumerate(chunk_list(datapoints, chunk_size)):
                    futures = [
                        executor.submit(
                            process_upload_with_context,
                            current_context,
                            datapoint,
                            chunk_idx * chunk_size + i,
                        )
                        for i, datapoint in enumerate(chunk)
                    ]

                    # Wait for this chunk to complete before starting the next one
                    for future in as_completed(futures):
                        if progress_tracking_error.is_set():
                            raise RuntimeError(
                                "Progress tracking failed, aborting uploads"
                            )

                        try:
                            chunk_successful, chunk_failed = future.result()
                            successful_uploads.extend(chunk_successful)
                            failed_uploads.extend(chunk_failed)
                        except Exception as e:
                            logger.error("Future execution failed: %s", str(e))
        finally:
            # Signal to the progress tracking thread that all uploads have been submitted
            stop_progress_tracking.set()

        return successful_uploads, failed_uploads

    def _log_final_progress(
        self,
        total_uploads: int,
        progress_poll_interval: float,
        successful_uploads: list[Datapoint],
        failed_uploads: list[Datapoint],
    ) -> None:
        """
        Log the final progress of the upload operation.

        Args:
            total_uploads: Total number of uploads
            initial_ready: Initial number of ready items
            initial_progress: Initial progress state
            progress_poll_interval: Time between progress checks
            successful_uploads: List of successful uploads for fallback reporting
            failed_uploads: List of failed uploads for fallback reporting
        """
        try:
            # Get final progress
            final_progress = (
                self.openapi_service.dataset_api.dataset_dataset_id_progress_get(
                    self.id
                )
            )
            total_ready = final_progress.ready
            total_failed = final_progress.failed

            # Make sure we account for all uploads
            if total_ready + total_failed < total_uploads:
                # Try one more time after a longer wait
                time.sleep(5 * progress_poll_interval)
                final_progress = (
                    self.openapi_service.dataset_api.dataset_dataset_id_progress_get(
                        self.id
                    )
                )
                total_ready = final_progress.ready
                total_failed = final_progress.failed

            success_rate = (
                (total_ready / total_uploads * 100) if total_uploads > 0 else 0
            )

            logger.info(
                "Upload complete: %s ready, %s failed (%s%% success rate)",
                total_ready,
                total_uploads - total_ready,
                success_rate,
            )
        except Exception as e:
            logger.error("Error getting final progress: %s", str(e))
            logger.info(
                "Upload summary from local tracking: %s succeeded, %s failed",
                len(successful_uploads),
                len(failed_uploads),
            )

        if failed_uploads:
            logger.error("Failed uploads: %s", failed_uploads)

    def _add_media_from_paths(
        self,
        datapoints: list[Datapoint],
        chunk_size: int = 50,
        progress_poll_interval: float = 0.5,
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        """
        Upload media paths in chunks with managed resources.

        Args:
            datapoints: List of Datapoint objects to upload
            chunk_size: Number of items to process in each batch
            progress_poll_interval: Time in seconds between progress checks
        Returns:
            tuple[list[Datapoint], list[Datapoint]]: Lists of successful and failed datapoints

        Raises:
            ValueError: If multi_metadata lengths don't match media_paths length
        """

        # Setup tracking variables
        total_uploads = len(datapoints)

        # Create thread control events
        stop_progress_tracking = threading.Event()
        progress_tracking_error = threading.Event()

        # Create and start progress tracking thread
        progress_thread = self._get_progress_tracker(
            total_uploads,
            stop_progress_tracking,
            progress_tracking_error,
            progress_poll_interval,
        )
        progress_thread.start()

        # Process uploads in chunks
        try:
            successful_uploads, failed_uploads = self._process_uploads_in_chunks(
                datapoints,
                chunk_size,
                stop_progress_tracking,
                progress_tracking_error,
            )
        finally:
            progress_thread.join(10)  # Add margin to the timeout for tqdm

        # Log final progress
        self._log_final_progress(
            total_uploads, progress_poll_interval, successful_uploads, failed_uploads
        )

        return successful_uploads, failed_uploads

    def __str__(self) -> str:
        return f"RapidataDataset(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
