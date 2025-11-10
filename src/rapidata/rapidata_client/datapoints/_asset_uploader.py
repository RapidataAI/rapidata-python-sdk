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
from rapidata.rapidata_client.config import rapidata_config
from cachetools import LRUCache


class AssetUploader:
    _shared_upload_cache: LRUCache = LRUCache(maxsize=100_000)

    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def _get_cache_key(self, asset: str) -> str:
        """Generate cache key for an asset."""
        if re.match(r"^https?://", asset):
            return asset
        else:
            if not os.path.exists(asset):
                raise FileNotFoundError(f"File not found: {asset}")
            
            stat = os.stat(asset)
            # Combine path, size, and modification time
            return f"{asset}:{stat.st_size}:{stat.st_mtime_ns}"

    def upload_asset(self, asset: str) -> str:
        with tracer.start_as_current_span("AssetUploader.upload_asset"):
            logger.debug("Uploading asset: %s", asset)
            assert isinstance(asset, str), "Asset must be a string"
            
            asset_key = self._get_cache_key(asset)
            if asset_key in self._shared_upload_cache:
                logger.debug("Asset found in cache")
                return self._shared_upload_cache[asset_key]

            if re.match(r"^https?://", asset):
                response = self.openapi_service.asset_api.asset_url_post(
                    url=asset,
                )
            else:
                response = self.openapi_service.asset_api.asset_file_post(
                    file=asset,
                )
            logger.info("Asset uploaded: %s", response.file_name)
            if rapidata_config.upload.cacheUploads:
                self._shared_upload_cache[asset_key] = response.file_name
                logger.debug("Asset added to cache")
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
