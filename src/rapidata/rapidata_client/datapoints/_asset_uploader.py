import re
import os
from rapidata.service.openapi_service import OpenAPIService


class AssetUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def upload_asset(self, asset: str) -> str:
        assert isinstance(asset, str), "Asset must be a string"

        if re.match(r"^https?://", asset):
            response = self.openapi_service.asset_api.asset_url_post(
                url=asset,
            )
        else:
            if not os.path.exists(asset):
                raise FileNotFoundError(f"File not found: {asset}")
            response = self.openapi_service.asset_api.asset_file_post(
                file=asset,
            )
        return response.file_name
