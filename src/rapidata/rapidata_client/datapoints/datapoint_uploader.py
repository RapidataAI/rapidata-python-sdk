import os
from rapidata.rapidata_client.datapoints.datapoint import Datapoint
from rapidata.rapidata_client.datapoints.metadata import MediaAssetMetadata
from rapidata.rapidata_client.datapoints.uploaded_datapoint import UploadedDatapoint
from rapidata.service.openapi_service import OpenAPIService
import re


class DatapointUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def upload_datapoint(self, datapoint: Datapoint) -> UploadedDatapoint:
        if MediaAssetMetadata in datapoint.metadata:
            for metadata in datapoint.metadata:
                if isinstance(metadata, MediaAssetMetadata):
                    pass

        if datapoint.data_type == "text":
            return UploadedDatapoint(
                file_names=[],
                data_type=datapoint.data_type,
                metadata=datapoint.metadata,
            )

        file_names = []
        for asset in datapoint.assets:
            if re.match(r"^https?://", asset):
                response = self.openapi_service.dataset_api.dataset_asset_url_post(
                    url=asset,
                )
            else:
                if not os.path.exists(asset):
                    raise FileNotFoundError(f"File not found: {asset}")
                response = self.openapi_service.dataset_api.dataset_asset_file_post(
                    file=asset,
                )
            file_names.append(response.file_name)
        return UploadedDatapoint(
            file_names=file_names,
            data_type=datapoint.data_type,
            metadata=datapoint.metadata,
        )
