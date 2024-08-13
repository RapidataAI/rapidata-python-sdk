from io import BufferedReader
from PIL import Image
from rapidata.service.rapidata_api_services.base_service import BaseRapidataAPIService
from rapidata.utils.image_utils import ImageUtils


class DatasetService(BaseRapidataAPIService):
    def __init__(self, client_id: str, client_secret: str, endpoint: str):
        super().__init__(
            client_id=client_id, client_secret=client_secret, endpoint=endpoint
        )

    def upload_text_sources(self, dataset_id: str, text_sources: list[str]):
        url = f"{self.endpoint}/Dataset/UploadTextSourcesToDataset"
        payload = {"datasetId": dataset_id, "textSources": text_sources}

        response = self._post(url, json=payload)

        return response

    def upload_images(
        self, dataset_id: str, images: list[Image.Image], image_names: list[str]
    ):
        url = f"{self.endpoint}/Dataset/UploadImagesToDataset"

        params = {"datasetId": dataset_id}

        images_bytes: list[bytes] = [
            ImageUtils.convert_PIL_image_to_bytes(image) for image in images
        ]

        files = [
            ("files", (image_name, image_bytes))
            for image_name, image_bytes in zip(image_names, images_bytes)
        ]

        response = self._post(url, params=params, files=files)

        return response

    def upload_videos(
        self, dataset_id: str, videos: list[BufferedReader], video_names: list[str]
    ):
        url = f"{self.endpoint}/Dataset/UploadImagesToDataset"

        params = {"datasetId": dataset_id}

        files = [
            ("files", (video_name, video_bytes))
            for video_name, video_bytes in zip(video_names, videos)
        ]

        response = self._post(url, params=params, files=files)

        return response

    def upload_images_from_s3(
        self,
        dataset_id: str,
        bucket_name: str,
        region: str,
        source_prefix: str,
        access_key: str,
        secret_key: str,
        clear_dataset: bool = True,
    ):
        url = f"{self.endpoint}/Dataset/UploadFilesFromS3"

        payload = {
            "datasetId": dataset_id,
            "bucketName": bucket_name,
            "region": region,
            "sourcePrefix": source_prefix,
            "accessKey": access_key,
            "secretKey": secret_key,
            "useCustomAwsCredentials": True,
            "clearDataset": clear_dataset,
        }

        response = self._post(url, json=payload)

        return response
