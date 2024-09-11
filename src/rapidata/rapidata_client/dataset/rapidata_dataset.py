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
from rapidata.service import LocalFileService
from rapidata.service.openapi_service import OpenAPIService
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


class RapidataDataset:

    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.dataset_id = dataset_id
        self.openapi_service = openapi_service
        self.local_file_service = LocalFileService()

    def add_texts(self, texts: list[str]):
        model = UploadTextSourcesToDatasetModel(
            datasetId=self.dataset_id, textSources=texts
        )
        self.openapi_service.dataset_api.dataset_upload_text_sources_to_dataset_post(
            model
        )

    def add_media_from_paths(
        self,
        image_paths: list[str | list[str]],
        metadata: list[Metadata] | None = None,
        max_workers: int = 10,
    ):
        if metadata is not None and len(metadata) != len(image_paths):
            raise ValueError(
                "metadata must be None or have the same length as image_paths"
            )

        def upload_datapoint(media_paths_rapid: str | list[str], meta: Metadata | None) -> None:
            if isinstance(media_paths_rapid, list) and not all(
                os.path.exists(media_path) for media_path in media_paths_rapid
            ):
                raise FileNotFoundError(f"File not found: {media_paths_rapid}")
            elif isinstance(media_paths_rapid, str) and not os.path.exists(
                media_paths_rapid
            ):
                raise FileNotFoundError(f"File not found: {media_paths_rapid}")

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
                files=media_paths_rapid if isinstance(media_paths_rapid, list) else [media_paths_rapid] # type: ignore
            )

        total_uploads = len(image_paths)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(upload_datapoint, media_paths, meta)
                for media_paths, meta in zip_longest(image_paths, metadata or [])
            ]

            with tqdm(total=total_uploads, desc="Uploading datapoints") as pbar:
                for future in as_completed(futures):
                    future.result()  # This will raise any exceptions that occurred during execution
                    pbar.update(1)
