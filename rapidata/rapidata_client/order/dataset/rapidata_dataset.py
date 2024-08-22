import os
from typing import List

from pydantic import StrictBytes, StrictStr
from openapi_client.api.dataset_api import DatasetApi
from openapi_client.models.datapoint_metadata_model import DatapointMetadataModel
from openapi_client.models.upload_text_sources_to_dataset_model import UploadTextSourcesToDatasetModel
from rapidata.service import LocalFileService
from rapidata.service.openapi_service import OpenAPIService


class RapidataDataset:

    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.dataset_id = dataset_id
        self.openapi_service = openapi_service
        self.local_file_service = LocalFileService()

    def add_texts(self, texts: list[str]):
        model = UploadTextSourcesToDatasetModel(datasetId=self.dataset_id, textSources=texts)
        self.openapi_service.dataset_api.dataset_upload_text_sources_to_dataset_post(model)

    def add_media_from_paths(self, image_paths: list[str]):
        model = DatapointMetadataModel(datasetId=self.dataset_id, metadata=[])

        self.openapi_service.dataset_api.dataset_create_datapoint_post(model=model, files=image_paths) # type: ignore