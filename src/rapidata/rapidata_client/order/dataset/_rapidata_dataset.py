from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from rapidata.rapidata_client.config import logger
import time
from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)
from rapidata.rapidata_client.config.rapidata_config import rapidata_config
from rapidata.rapidata_client.datapoints._datapoint_uploader import DatapointUploader

# Add OpenTelemetry context imports for thread propagation
from opentelemetry import context as otel_context


class RapidataDataset:
    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.id = dataset_id
        self.openapi_service = openapi_service
        self.datapoint_uploader = DatapointUploader(openapi_service)

    def add_datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        """
        Process uploads concurrently with a ThreadPoolExecutor.

        Args:
            datapoints: List of datapoints to upload

        Returns:
            tuple[list[Datapoint], list[Datapoint]]: Lists of successful and failed uploads
        """
        successful_uploads: list[Datapoint] = []
        failed_uploads: list[Datapoint] = []

        with tqdm(
            total=len(datapoints),
            desc="Uploading datapoints",
            disable=rapidata_config.logging.silent_mode,
        ) as progress_bar:

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
                # Submit all uploads at once - executor manages concurrency via max_workers
                futures = [
                    executor.submit(
                        process_upload_with_context,
                        current_context,
                        datapoint,
                        i,
                    )
                    for i, datapoint in enumerate(datapoints)
                ]

                # Process results as they complete (no blocking on chunks)
                for future in as_completed(futures):
                    try:
                        upload_successful, upload_failed = future.result()
                        successful_uploads.extend(upload_successful)
                        failed_uploads.extend(upload_failed)
                        progress_bar.update(len(upload_successful))
                    except Exception as e:
                        logger.error("Future execution failed: %s", str(e))

        if failed_uploads:
            logger.error(
                "Upload failed for %s datapoints: %s",
                len(failed_uploads),
                failed_uploads,
            )

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

        last_exception = None
        for attempt in range(rapidata_config.upload.maxRetries):
            try:
                with suppress_rapidata_error_logging():
                    self.datapoint_uploader.upload_datapoint(
                        dataset_id=self.id,
                        datapoint=datapoint,
                        index=index,
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

    def __str__(self) -> str:
        return f"RapidataDataset(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
