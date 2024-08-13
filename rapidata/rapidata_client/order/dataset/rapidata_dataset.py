import os
from rapidata.service import LocalFileService
from rapidata.service import RapidataService


class RapidataDataset:

    def __init__(self, dataset_id: str, rapidata_service: RapidataService):
        self.dataset_id = dataset_id
        self.rapidata_service = rapidata_service
        self.local_file_service = LocalFileService()

    def add_texts(self, texts: list[str]):
        self.rapidata_service.dataset.upload_text_sources(self.dataset_id, texts)

    def add_images_from_paths(self, image_paths: list[str]):
        image_names = [os.path.basename(image_path) for image_path in image_paths]
        images = self.local_file_service.load_images(image_paths)

        self.rapidata_service.dataset.upload_images(self.dataset_id, images, image_names)

    def add_videos_from_paths(self, video_paths: list[str]):
        video_names = [os.path.basename(video_path) for video_path in video_paths]
        videos = self.local_file_service.load_videos(video_paths)

        self.rapidata_service.dataset.upload_videos(self.dataset_id, videos, video_names)