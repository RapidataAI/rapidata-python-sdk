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
        chunk_size: int = 50  # Process in smaller chunks
    ) -> tuple[list[str], list[str]]:
        """
        Upload media paths in chunks with managed resources.
        """
        if metadata is not None and len(metadata) != len(media_paths):
            raise ValueError("metadata must be None or have the same length as media_paths")
        
        # Create a session with optimized connection pool
        session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True
        )
        
        # Increase pool size and configure timeouts
        adapter = HTTPAdapter(
            pool_connections=max_workers * 2,
            pool_maxsize=max_workers * 4,
            max_retries=retries
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        def upload_datapoint(media_asset: MediaAsset | MultiAsset, 
                            meta: Metadata | None, 
                            index: int,
                            session: requests.Session) -> tuple[list[str], list[str]]:
            local_successful: list[str] = []
            local_failed: list[str] = []
            urls_to_track = []

            try:
                # Collect URLs for tracking
                if isinstance(media_asset, MediaAsset) and media_asset._url:
                    urls_to_track.append(media_asset._url)
                elif isinstance(media_asset, MultiAsset):
                    for asset in media_asset.assets:
                        if isinstance(asset, MediaAsset):
                            urls_to_track.append(asset._url)

                if isinstance(media_asset, MediaAsset):
                    assets = [media_asset]
                elif isinstance(media_asset, MultiAsset):
                    assets = media_asset.assets
                else:
                    raise ValueError(f"Unsupported asset type: {type(media_asset)}")

                # Prepare the upload
                meta_model = meta.to_model() if meta else None
                model = DatapointMetadataModel(
                    datasetId=self.dataset_id,
                    metadata=([DatapointMetadataModelMetadataInner(meta_model)] if meta_model else []),
                    sortIndex=index,
                )

                files: list[tuple[StrictStr, StrictBytes] | StrictStr | StrictBytes] = []
                for asset in assets:
                    if isinstance(asset, MediaAsset):
                        # Pass the session to MediaAsset for reuse
                        asset._session = session
                        files.append(asset.to_file())

                upload_response = self.openapi_service.dataset_api.dataset_create_datapoint_post(
                    model=model,
                    files=files
                )

                if upload_response.errors:
                    raise ValueError(f"Error uploading datapoint: {upload_response.errors}")

                local_successful.extend(urls_to_track)

            except Exception as e:
                self._logger.error(f"Failed to upload: {str(e)}")
                local_failed.extend(urls_to_track)

            return local_successful, local_failed
        
        successful_uploads: list[str] = []
        failed_uploads: list[str] = []
        total_uploads = len(media_paths)

        # Process in chunks to prevent resource exhaustion
        with tqdm(total=total_uploads, desc="Uploading datapoints") as pbar:
            for chunk_idx, chunk in enumerate(chunk_list(media_paths, chunk_size)):
                chunk_metadata = metadata[chunk_idx * chunk_size:(chunk_idx + 1) * chunk_size] if metadata else None
                
                # Create a new thread pool for each chunk
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
                            self._logger.error(f"Chunk processing failed: {str(e)}")
                        finally:
                            pbar.update(1)

                # Small delay between chunks to allow resources to be freed
                time.sleep(1)

        success_rate = len(successful_uploads) / total_uploads * 100 if total_uploads > 0 else 0
        self._logger.info(f"Upload complete: {len(successful_uploads)} successful, {len(failed_uploads)} failed ({success_rate:.1f}% success rate)")

        if failed_uploads:
            print(f"Failed uploads: {failed_uploads}")

        return successful_uploads, failed_uploads
