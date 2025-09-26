from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from tqdm import tqdm

from rapidata.rapidata_client.config import logger
from rapidata.api_client.models.create_sample_model import CreateSampleModel
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config.rapidata_config import rapidata_config
from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)

from opentelemetry import context as otel_context
from rapidata.api_client.models.create_sample_model_asset import CreateSampleModelAsset
from rapidata.api_client.models.existing_asset_input import ExistingAssetInput
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader


class BenchmarkParticipant:
    def __init__(self, name: str, id: str, openapi_service: OpenAPIService):
        self.name = name
        self.id = id
        self._openapi_service = openapi_service
        self._asset_uploader = AssetUploader(openapi_service)

    def _process_single_sample_upload(
        self,
        asset: str,
        identifier: str,
    ) -> tuple[str | None, str | None]:
        """
        Process single sample upload with retry logic and error tracking.

        Args:
            asset: MediaAsset to upload
            identifier: Identifier for the sample

        Returns:
            tuple[MediaAsset | None, MediaAsset | None]: (successful_asset, failed_asset)
        """

        last_exception = None
        for attempt in range(rapidata_config.upload.maxRetries):
            try:
                with suppress_rapidata_error_logging():
                    self._openapi_service.participant_api.participant_participant_id_sample_new_post(
                        participant_id=self.id,
                        create_sample_model=CreateSampleModel(
                            identifier=identifier,
                            asset=CreateSampleModelAsset(
                                actual_instance=ExistingAssetInput(
                                    _t="ExistingAssetInput",
                                    name=self._asset_uploader.upload_asset(asset),
                                ),
                            ),
                        ),
                    )

                return asset, None

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

        logger.error(f"Upload failed for {identifier}. Error: {str(last_exception)}")
        return None, asset

    def upload_media(
        self,
        assets: list[str],
        identifiers: list[str],
    ) -> tuple[list[str], list[str]]:
        """
        Upload samples concurrently with proper error handling and progress tracking.

        Args:
            assets: List of strings to upload
            identifiers: List of identifiers matching the assets

        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed identifiers
        """

        def upload_with_context(
            context: otel_context.Context, asset: str, identifier: str
        ) -> tuple[str | None, str | None]:
            """Wrapper function that runs _process_single_sample_upload with the provided context."""
            token = otel_context.attach(context)
            try:
                return self._process_single_sample_upload(asset, identifier)
            finally:
                otel_context.detach(token)

        successful_uploads: list[str] = []
        failed_uploads: list[str] = []
        total_uploads = len(assets)

        # Capture the current OpenTelemetry context before creating threads
        current_context = otel_context.get_current()

        with ThreadPoolExecutor(
            max_workers=rapidata_config.upload.maxWorkers
        ) as executor:
            futures = [
                executor.submit(
                    upload_with_context,
                    current_context,
                    asset,
                    identifier,
                )
                for asset, identifier in zip(assets, identifiers)
            ]

            with tqdm(
                total=total_uploads,
                desc="Uploading media",
                disable=rapidata_config.logging.silent_mode,
            ) as pbar:
                for future in as_completed(futures):
                    try:
                        successful_id, failed_id = future.result()
                        if successful_id:
                            successful_uploads.append(successful_id)
                            pbar.update(1)
                        if failed_id:
                            failed_uploads.append(failed_id)
                    except Exception as e:
                        logger.error(f"Future execution failed: {str(e)}")

        return successful_uploads, failed_uploads
