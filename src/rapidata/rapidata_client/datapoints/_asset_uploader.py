import re
import os
from rapidata.api_client.models.existing_asset_input import ExistingAssetInput
from rapidata.api_client.models.multi_asset_input import (
    MultiAssetInput,
    MultiAssetInputAssetsInner,
)
from rapidata.api_client.models.text_asset_input import TextAssetInput
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config import tracer


class AssetUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def upload_asset(self, asset: str) -> str:
        with tracer.start_as_current_span("AssetUploader.upload_asset"):
            logger.debug("Uploading asset: %s", asset)
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

    def get_uploaded_text_input(
        self, assets: list[str] | str
    ) -> MultiAssetInput | TextAssetInput:
        if isinstance(assets, list):
            return MultiAssetInput(
                _t="MultiAssetInput",
                assets=[
                    MultiAssetInputAssetsInner(
                        actual_instance=TextAssetInput(_t="TextAssetInput", text=asset)
                    )
                    for asset in assets
                ],
            )
        else:
            return TextAssetInput(_t="TextAssetInput", text=assets)

    def get_uploaded_asset_input(
        self, assets: list[str] | str
    ) -> MultiAssetInput | ExistingAssetInput:
        if isinstance(assets, list):
            return MultiAssetInput(
                _t="MultiAssetInput",
                assets=[
                    MultiAssetInputAssetsInner(
                        actual_instance=ExistingAssetInput(
                            _t="ExistingAssetInput",
                            name=self.upload_asset(asset),
                        ),
                    )
                    for asset in assets
                ],
            )
        else:
            return ExistingAssetInput(
                _t="ExistingAssetInput",
                name=self.upload_asset(assets),
            )
