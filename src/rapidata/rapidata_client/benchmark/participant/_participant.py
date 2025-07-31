from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from tqdm import tqdm

from rapidata.rapidata_client.datapoints.assets import MediaAsset
from rapidata.rapidata_client.logging import logger
from rapidata.rapidata_client.logging.output_manager import RapidataOutputManager
from rapidata.api_client.models.create_sample_model import CreateSampleModel
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config.config import rapidata_config
from rapidata.rapidata_client.api.rapidata_exception import (
    suppress_rapidata_error_logging,
)


class BenchmarkParticipant:
    def __init__(self, name: str, id: str, openapi_service: OpenAPIService):
        self.name = name
        self.id = id
        self.__openapi_service = openapi_service

    def _process_single_sample_upload(
        self,
        asset: MediaAsset,
        identifier: str,
    ) -> tuple[MediaAsset | None, MediaAsset | None]:
        """
        Process single sample upload with retry logic and error tracking.

        Args:
            asset: MediaAsset to upload
            identifier: Identifier for the sample

        Returns:
            tuple[MediaAsset | None, MediaAsset | None]: (successful_asset, failed_asset)
        """
        if asset.is_local():
            files = [asset.to_file()]
            urls = []
        else:
            files = []
            urls = [asset.path]

        last_exception = None
        for attempt in range(rapidata_config.upload_max_retries):
            try:
                with suppress_rapidata_error_logging():
                    self.__openapi_service.participant_api.participant_participant_id_sample_post(
                        participant_id=self.id,
                        model=CreateSampleModel(identifier=identifier),
                        files=files,
                        urls=urls,
                    )

                return asset, None

            except Exception as e:
                last_exception = e
                if attempt < rapidata_config.upload_max_retries - 1:
                    # Exponential backoff: wait 1s, then 2s, then 4s
                    retry_delay = 2**attempt
                    time.sleep(retry_delay)
                    logger.debug("Error: %s", str(last_exception))
                    logger.debug(
                        "Retrying %s of %s...",
                        attempt + 1,
                        rapidata_config.upload_max_retries,
                    )

        logger.error(f"Upload failed for {identifier}. Error: {str(last_exception)}")
        return None, asset

    def upload_media(
        self,
        assets: list[MediaAsset],
        identifiers: list[str],
    ) -> tuple[list[MediaAsset], list[MediaAsset]]:
        """
        Upload samples concurrently with proper error handling and progress tracking.

        Args:
            assets: List of MediaAsset objects to upload
            identifiers: List of identifiers matching the assets

        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed identifiers
        """
        successful_uploads: list[MediaAsset] = []
        failed_uploads: list[MediaAsset] = []
        total_uploads = len(assets)

        with ThreadPoolExecutor(
            max_workers=rapidata_config.max_upload_workers
        ) as executor:
            futures = [
                executor.submit(
                    self._process_single_sample_upload,
                    asset,
                    identifier,
                )
                for asset, identifier in zip(assets, identifiers)
            ]

            with tqdm(
                total=total_uploads,
                desc="Uploading media",
                disable=RapidataOutputManager.silent_mode,
            ) as pbar:
                for future in as_completed(futures):
                    try:
                        successful_id, failed_id = future.result()
                        if successful_id:
                            successful_uploads.append(successful_id)
                        if failed_id:
                            failed_uploads.append(failed_id)
                    except Exception as e:
                        logger.error(f"Future execution failed: {str(e)}")

                    pbar.update(1)

        return successful_uploads, failed_uploads
