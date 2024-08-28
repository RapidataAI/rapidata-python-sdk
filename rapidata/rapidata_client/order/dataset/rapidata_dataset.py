from itertools import zip_longest
import os
from typing import List

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
        image_paths: list[str],
        metadata: List[Metadata] | None = None,
    ):
        if metadata is not None and len(metadata) != len(image_paths):
            raise ValueError(
                "metadata must be None or have the same length as image_paths"
            )

        for image_path, meta in zip_longest(image_paths, metadata or []):
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"File not found: {image_path}")
            
            meta_model = meta.to_model() if meta else None
            model = DatapointMetadataModel(
                datasetId=self.dataset_id,
                metadata=[DatapointMetadataModelMetadataInner(meta_model)] if meta_model else [],
            )

            self.openapi_service.dataset_api.dataset_create_datapoint_post(model=model, files=[image_path])  # type: ignore
