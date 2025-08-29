from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.datapoints.assets import TextAsset, MediaAsset
from rapidata.service import LocalFileService
from rapidata.service.openapi_service import OpenAPIService
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from typing import Generator
from rapidata.rapidata_client.config import logger
import time
import threading
from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)
from rapidata.rapidata_client.config.rapidata_config import rapidata_config
from rapidata.rapidata_client.order.dataset._progress_tracker import ProgressTracker

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

    def _process_uploads_in_chunks(
        self,
        datapoints: list[Datapoint],
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        """
        Process uploads in chunks with a ThreadPoolExecutor.

        Args:
            media_paths: List of assets to upload
            multi_metadata: Optional sequence of sequences of metadata
            chunk_size: Number of items to process in each batch

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

        with ThreadPoolExecutor(
            max_workers=rapidata_config.upload.maxWorkers
        ) as executor:
            # Process uploads in chunks to avoid overwhelming the system
            for chunk_idx, chunk in enumerate(
                chunk_list(datapoints, rapidata_config.upload.chunkSize)
            ):
                futures = [
                    executor.submit(
                        process_upload_with_context,
                        current_context,
                        datapoint,
                        chunk_idx * rapidata_config.upload.chunkSize + i,
                    )
                    for i, datapoint in enumerate(chunk)
                ]

                # Wait for this chunk to complete before starting the next one
                for future in as_completed(futures):
                    try:
                        chunk_successful, chunk_failed = future.result()
                        successful_uploads.extend(chunk_successful)
                        failed_uploads.extend(chunk_failed)
                    except Exception as e:
                        logger.error("Future execution failed: %s", str(e))

        return successful_uploads, failed_uploads

    def _add_media_from_paths(
        self,
        datapoints: list[Datapoint],
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

        # Create and start progress tracking thread
        progress_tracker = ProgressTracker(
            dataset_id=self.id,
            openapi_service=self.openapi_service,
            total_uploads=total_uploads,
            progress_poll_interval=progress_poll_interval,
        )
        progress_thread = progress_tracker.create_thread()
        progress_thread.start()

        # Process uploads in chunks
        try:
            successful_uploads, failed_uploads = self._process_uploads_in_chunks(
                datapoints,
            )
        finally:
            progress_tracker.complete()
            progress_thread.join(10)

        if failed_uploads:
            logger.error(
                "Upload failed for %s datapoints: %s",
                len(failed_uploads),
                failed_uploads,
            )

        return successful_uploads, failed_uploads

    def __str__(self) -> str:
        return f"RapidataDataset(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
