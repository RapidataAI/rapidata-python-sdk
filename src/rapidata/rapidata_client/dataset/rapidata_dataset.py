from itertools import zip_longest
import os

from rapidata.api_client.models.datapoint_metadata_model import DatapointMetadataModel
from rapidata.api_client.models.datapoint_metadata_model_metadata_inner import (
    DatapointMetadataModelMetadataInner,
)
from rapidata.api_client.models.upload_text_sources_to_dataset_model import (
    UploadTextSourcesToDatasetModel,
)
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.rapidata_client.assets import TextAsset, MediaAsset, MultiAsset
from rapidata.service import LocalFileService
from rapidata.service.openapi_service import OpenAPIService
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


class RapidataDataset:

    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.dataset_id = dataset_id
        self.openapi_service = openapi_service
        self.local_file_service = LocalFileService()

    def add_texts(self, text_assets: list[TextAsset]):
        texts = [text.text for text in text_assets]
        model = UploadTextSourcesToDatasetModel(
            datasetId=self.dataset_id, textSources=texts
        )
        self.openapi_service.dataset_api.dataset_upload_text_sources_to_dataset_post(
            model
        )

    def add_media_from_paths(
        self,
        media_paths: list[MediaAsset | MultiAsset],
        metadata: list[Metadata] | None = None,
        max_workers: int = 10,
    ):
        if metadata is not None and len(metadata) != len(media_paths):
            raise ValueError(
                "metadata must be None or have the same length as media_paths"
            )

        def upload_datapoint(media_asset: MediaAsset | MultiAsset, meta: Metadata | None) -> None:
            if isinstance(media_asset, MediaAsset):
                paths = [media_asset.path]
            elif isinstance(media_asset, MultiAsset):
                paths = [asset.path for asset in media_asset.assets if isinstance(asset, MediaAsset)]
            else:
                raise ValueError(f"Unsupported asset type: {type(media_asset)}")
            
            assert all(
                os.path.exists(media_path) for media_path in paths
            ), "All media paths must exist on the local filesystem."

            meta_model = meta.to_model() if meta else None
            model = DatapointMetadataModel(
                datasetId=self.dataset_id,
                metadata=(
                    [DatapointMetadataModelMetadataInner(meta_model)]
                    if meta_model
                    else []
                ),
            )

            self.openapi_service.dataset_api.dataset_create_datapoint_post(
                model=model,
                files=paths # type: ignore
            )

        total_uploads = len(media_paths)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(upload_datapoint, media_asset, meta)
                for media_asset, meta in zip_longest(media_paths, metadata or [])
            ]

            with tqdm(total=total_uploads, desc="Uploading datapoints") as pbar:
                for future in as_completed(futures):
                    future.result()  # This will raise any exceptions that occurred during execution
                    pbar.update(1)
