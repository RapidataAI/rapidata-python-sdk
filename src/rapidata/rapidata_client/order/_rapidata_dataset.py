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

from typing import cast, Sequence


class RapidataDataset:

    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.dataset_id = dataset_id
        self.openapi_service = openapi_service
        self.local_file_service = LocalFileService()

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

        def upload_text_datapoint(text_asset: TextAsset | MultiAsset) -> None:
            if isinstance(text_asset, TextAsset):
                texts = [text_asset.text]
            elif isinstance(text_asset, MultiAsset):
                texts = [asset.text for asset in text_asset.assets if isinstance(asset, TextAsset)]
            else:
                raise ValueError(f"Unsupported asset type: {type(text_asset)}")

            model = UploadTextSourcesToDatasetModel(
                datasetId=self.dataset_id,
                textSources=texts
            )

            upload_response = self.openapi_service.dataset_api.dataset_creat_text_datapoint_post(model)

            if upload_response.errors:
                raise ValueError(f"Error uploading text datapoint: {upload_response.errors}")

        total_uploads = len(text_assets)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(upload_text_datapoint, text_asset)
                for text_asset in text_assets
            ]

            with tqdm(total=total_uploads, desc="Uploading text datapoints") as pbar:
                for future in as_completed(futures):
                    future.result()  # This will raise any exceptions that occurred during execution
                    pbar.update(1)

    def _add_media_from_paths(
        self,
        media_paths: list[MediaAsset] |  list[MultiAsset], # where multiasset is a list of media assets
        metadata: Sequence[Metadata] | None = None,
        max_workers: int = 10,
    ):
        if metadata is not None and len(metadata) != len(media_paths):
            raise ValueError(
                "metadata must be None or have the same length as media_paths"
            )
        
        for media_path in media_paths:
            if isinstance(media_path, MultiAsset):
                assert all(
                    isinstance(asset, MediaAsset) for asset in media_path.assets
                ), "All assets in a MultiAsset must be of type MediaAsset."

        def upload_datapoint(media_asset: MediaAsset | MultiAsset, meta: Metadata | None) -> None:
            if isinstance(media_asset, MediaAsset):
                assets = [media_asset]
            elif isinstance(media_asset, MultiAsset):
                assets = media_asset.assets
            else:
                raise ValueError(f"Unsupported asset type: {type(media_asset)}")

            meta_model = meta._to_model() if meta else None
            model = DatapointMetadataModel(
                datasetId=self.dataset_id,
                metadata=(
                    [DatapointMetadataModelMetadataInner(meta_model)]
                    if meta_model
                    else []
                ),
            )

            files: list[tuple[str, bytes] | str] = []
            for asset in assets:
                if isinstance(asset, MediaAsset):
                    if isinstance(asset.path, bytes):
                        files.append((asset.name, asset.path))
                    else:
                        files.append(cast(str, asset.path))

            upload_response = self.openapi_service.dataset_api.dataset_create_datapoint_post(
                model=model,
                files=files # type: ignore
            )
            if upload_response.errors:
                raise ValueError(f"Error uploading datapoint: {upload_response.errors}")

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
