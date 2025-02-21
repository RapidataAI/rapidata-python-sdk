from itertools import zip_longest

from rapidata.api_client.models.datapoint_metadata_model import DatapointMetadataModel
from rapidata.api_client.models.datapoint_metadata_model_metadata_inner import (
    DatapointMetadataModelMetadataInner,
)
from rapidata.api_client.models.upload_text_sources_to_dataset_model import (
    UploadTextSourcesToDatasetModel,
)
from rapidata.rapidata_client.metadata._base_metadata import Metadata
from rapidata.rapidata_client.assets import TextAsset, MediaAsset, MultiAsset
from rapidata.service import LocalFileService
from rapidata.service.openapi_service import OpenAPIService
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from pydantic import StrictBytes, StrictStr
from typing import Optional, cast, Sequence, Generator
from logging import Logger
from requests.adapters import HTTPAdapter, Retry
import time
import requests


def chunk_list(lst: list, chunk_size: int) -> Generator:
    """Split list into chunks to prevent resource exhaustion"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

class RapidataDataset:

    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.dataset_id = dataset_id
        self.openapi_service = openapi_service
        self.local_file_service = LocalFileService()
        self._logger = Logger(__name__)

    def _add_texts(
        self,
        text_assets: list[TextAsset] | list[MultiAsset],
        max_workers: int = 10,
    ):
        for text_asset in text_assets:
            if isinstance(text_asset, MultiAsset):
                assert all(
                    isinstance(asset, TextAsset) for asset in text_asset.assets
                ), "All assets in a MultiAsset must be of type TextAsset."

        def upload_text_datapoint(text_asset: TextAsset | MultiAsset, index: int) -> None:
            if isinstance(text_asset, TextAsset):
                texts = [text_asset.text]
            elif isinstance(text_asset, MultiAsset):
                texts = [asset.text for asset in text_asset.assets if isinstance(asset, TextAsset)]
            else:
                raise ValueError(f"Unsupported asset type: {type(text_asset)}")

            model = UploadTextSourcesToDatasetModel(
                datasetId=self.dataset_id,
                textSources=texts,
                sortIndex=index,
            )

            upload_response = self.openapi_service.dataset_api.dataset_creat_text_datapoint_post(model)

            if upload_response.errors:
                raise ValueError(f"Error uploading text datapoint: {upload_response.errors}")

        total_uploads = len(text_assets)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(upload_text_datapoint, text_asset, index=i)
                for i, text_asset in enumerate(text_assets)
            ]

            with tqdm(total=total_uploads, desc="Uploading text datapoints") as pbar:
                for future in as_completed(futures):
                    future.result()  # This will raise any exceptions that occurred during execution
                    pbar.update(1)

    def _add_media_from_paths(
        self,
        media_paths: list[MediaAsset] | list[MultiAsset],
        metadata: Sequence[Metadata] | None = None,
        max_workers: int = 10,
        max_retries: int = 5,
        chunk_size: int = 50,
    ) -> tuple[list[str], list[str]]:
        """
        Upload media paths in chunks with managed resources.
        
        Args:
            media_paths: List of MediaAsset or MultiAsset objects to upload
            metadata: Optional sequence of metadata matching media_paths length
            max_workers: Maximum number of concurrent upload workers
            max_retries: Maximum number of retry attempts per failed request
            chunk_size: Number of items to process in each batch
            
        Returns:
            tuple[list[str], list[str]]: Lists of successful and failed URLs
            
        Raises:
            ValueError: If metadata length doesn't match media_paths length
        """
        if metadata is not None and len(metadata) != len(media_paths):
            raise ValueError("metadata must be None or have the same length as media_paths")

        # Configure session with retry logic
        session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(
            pool_connections=max_workers * 2,
            pool_maxsize=max_workers * 4,
            max_retries=retries
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        def upload_datapoint(
            media_asset: MediaAsset | MultiAsset, 
            meta: Metadata | None, 
            index: int,
            session: requests.Session
        ) -> tuple[list[str], list[str]]:
            """Process single upload with error tracking."""
            local_successful: list[str] = []
            local_failed: list[str] = []
            identifiers_to_track: list[str] = []
            
            try:
                # Get identifier for this upload (URL or file path)
                if isinstance(media_asset, MediaAsset):
                    media_asset.session = session
                    assets = [media_asset]
                    identifier = media_asset._url if media_asset._url else media_asset.path
                    identifiers_to_track = [identifier] if identifier else []
                elif isinstance(media_asset, MultiAsset):
                    assets = cast(list[MediaAsset], media_asset.assets)
                    for asset in assets:
                        asset.session = session
                    identifiers_to_track: list[str] = [
                        (asset._url if asset._url else cast(str, asset.path)) 
                        for asset in assets
                    ]
                else:
                    raise ValueError(f"Unsupported asset type: {type(media_asset)}")

                meta_model = meta.to_model() if meta else None
                model = DatapointMetadataModel(
                    datasetId=self.dataset_id,
                    metadata=([DatapointMetadataModelMetadataInner(meta_model)] if meta_model else []),
                    sortIndex=index,
                )

                files: list[tuple[StrictStr, StrictBytes] | StrictStr | StrictBytes] = []
                for asset in assets:
                    if isinstance(asset, MediaAsset):
                        files.append(asset.to_file())

                upload_response = self.openapi_service.dataset_api.dataset_create_datapoint_post(
                    model=model,
                    files=files
                )

                if upload_response.errors:
                    error_msg = f"Error uploading datapoint: {upload_response.errors}"
                    self._logger.error(error_msg)
                    local_failed.extend(identifiers_to_track)
                    raise ValueError(error_msg)

                local_successful.extend(identifiers_to_track)

            except Exception as e:
                self._logger.error(f"\nUpload failed for {identifiers_to_track}: {str(e)}") # \n to avoid same line as tqdm
                local_failed.extend(identifiers_to_track)

            return local_successful, local_failed


        # Process uploads in chunks
        successful_uploads: list[str] = []
        failed_uploads: list[str] = []
        total_uploads = len(media_paths)

        with tqdm(total=total_uploads, desc="Uploading datapoints") as pbar:
            for chunk_idx, chunk in enumerate(chunk_list(media_paths, chunk_size)):
                chunk_metadata = metadata[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size] if metadata else None
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(
                            upload_datapoint, 
                            media_asset, 
                            meta, 
                            index=(chunk_idx * chunk_size + i),
                            session=session
                        )
                        for i, (media_asset, meta) in enumerate(zip_longest(chunk, chunk_metadata or []))
                    ]

                    for future in as_completed(futures):
                        try:
                            chunk_successful, chunk_failed = future.result()
                            successful_uploads.extend(chunk_successful)
                            failed_uploads.extend(chunk_failed)
                        except Exception as e:
                            self._logger.error(f"Future execution failed: {str(e)}")
                        finally:
                            pbar.update(1)

        # Log summary statistics
        success_rate = len(successful_uploads) / total_uploads * 100 if total_uploads > 0 else 0
        self._logger.info(f"Upload complete: {len(successful_uploads)} successful, {len(failed_uploads)} failed ({success_rate:.1f}% success rate)")

        if failed_uploads:
            print(f"Failed uploads: {failed_uploads}")

        return successful_uploads, failed_uploads

