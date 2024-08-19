import os
from typing import List

from pydantic import StrictBytes, StrictStr
from openapi_client.api.dataset_api import DatasetApi
from openapi_client.api_client import ApiClient
from openapi_client.models.upload_text_sources_to_dataset_model import UploadTextSourcesToDatasetModel
from rapidata.service import LocalFileService


from rapidata.service.rapidata_api_services.rapidata_service import RapidataService
from rapidata.utils.image_utils import ImageUtils
class RapidataDataset:

    def __init__(self, dataset_id: str, api_client: ApiClient, rapidata_service: RapidataService):
        self.dataset_id = dataset_id
        self.api_client = api_client
        self.rapidata_service = rapidata_service
        self.dataset_api = DatasetApi(api_client)
        self.local_file_service = LocalFileService()

    def add_texts(self, texts: list[str]):
        model = UploadTextSourcesToDatasetModel(datasetId=self.dataset_id, textSources=texts)
        self.dataset_api.dataset_upload_text_sources_to_dataset_post(model)

    def add_images_from_paths(self, image_paths: list[str]):
        image_names = [os.path.basename(image_path) for image_path in image_paths]
        images = self.local_file_service.load_images(image_paths)

        self.rapidata_service.dataset.upload_images(self.dataset_id, images, image_names)

    def add_videos_from_paths(self, video_paths: list[str]):
        video_names = [os.path.basename(video_path) for video_path in video_paths]
        videos = self.local_file_service.load_videos(video_paths)

        # self.api_client.dataset.upload_videos(self.dataset_id, videos, video_names)