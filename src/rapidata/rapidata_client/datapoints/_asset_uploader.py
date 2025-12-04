from __future__ import annotations

import re
import os
from typing import TYPE_CHECKING, cast

from rapidata.rapidata_client.config.upload_config import register_upload_config_handler
from rapidata.rapidata_client.config.upload_config import UploadConfig
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config import tracer
from rapidata.rapidata_client.config import rapidata_config
from diskcache import FanoutCache

if TYPE_CHECKING:
    from rapidata.api_client.models.i_asset_input import IAssetInput


class AssetUploader:
    _shared_upload_cache: FanoutCache = FanoutCache(
        rapidata_config.upload.cacheLocation,
        shards=rapidata_config.upload.maxWorkers,
        timeout=rapidata_config.upload.cacheTimeout,
        size_limit=rapidata_config.upload.cacheSizeLimit,
    )

    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        # Register the handler for config update changes
        register_upload_config_handler(self._handle_config_update)

    @classmethod
    def _handle_config_update(cls, config: UploadConfig):
        """
        Handle updates to the upload config (e.g., cache location, size, workers, timeout).
        Re-instantiates the shared cache based on the new configuration.
        """
        logger.debug("Updating AssetUploader shared upload cache with new config")
        try:
            # Dispose of the old cache (closes open resources)
            old_cache = getattr(cls, "_shared_upload_cache", None)
            if old_cache:
                try:
                    old_cache.close()
                except Exception:
                    pass  # ignore close errors

            # Re-initialize with the updated config
            cls._shared_upload_cache = FanoutCache(
                config.cacheLocation,
                shards=config.maxWorkers,
                timeout=config.cacheTimeout,
                size_limit=config.cacheSizeLimit,
            )
            logger.info(
                "AssetUploader shared upload cache updated: location=%s, shards=%s, timeout=%s, size_limit=%s",
                config.cacheLocation,
                config.maxWorkers,
                config.cacheTimeout,
                config.cacheSizeLimit,
            )
        except Exception as e:
            logger.warning(f"Failed to update AssetUploader shared upload cache: {e}")

    def _get_cache_key(self, asset: str) -> str:
        """Generate cache key for an asset, including environment."""
        env = self.openapi_service.environment
        if not os.path.exists(asset):
            raise FileNotFoundError(f"File not found: {asset}")

        stat = os.stat(asset)
        return f"{env}@{asset}:{stat.st_size}:{stat.st_mtime_ns}"

    def upload_asset(self, asset: str) -> str:
        with tracer.start_as_current_span("AssetUploader.upload_asset"):
            logger.debug("Uploading asset: %s", asset)
            assert isinstance(asset, str), "Asset must be a string"
            if re.match(r"^https?://", asset):
                response = self.openapi_service.asset_api.asset_url_post(
                    url=asset,
                )
                return response.file_name

            asset_key = self._get_cache_key(asset)
            cached_value = self._shared_upload_cache.get(asset_key)
            if cached_value is not None:
                logger.debug("Asset found in cache")
                return cast(str, cached_value)  # Type hint for the linter

            response = self.openapi_service.asset_api.asset_file_post(
                file=asset,
            )
            if rapidata_config.upload.cacheUploads:
                self._shared_upload_cache[asset_key] = response.file_name
                logger.debug("Asset added to cache")
            logger.info("Asset uploaded: %s", response.file_name)
            return response.file_name

    def get_uploaded_text_input(self, assets: list[str] | str) -> IAssetInput:
        from rapidata.api_client.models.i_asset_input import IAssetInput
        from rapidata.api_client.models.i_asset_input_text_asset_input import (
            IAssetInputTextAssetInput,
        )
        from rapidata.api_client.models.i_asset_input_multi_asset_input import (
            IAssetInputMultiAssetInput,
        )

        if isinstance(assets, list):
            return IAssetInput(
                actual_instance=IAssetInputMultiAssetInput(
                    _t="MultiAssetInput",
                    assets=[
                        IAssetInput(
                            actual_instance=IAssetInputTextAssetInput(
                                _t="TextAssetInput", text=asset
                            )
                        )
                        for asset in assets
                    ],
                )
            )
        else:
            return IAssetInput(
                actual_instance=IAssetInputTextAssetInput(
                    _t="TextAssetInput", text=assets
                )
            )

    def get_uploaded_asset_input(self, assets: list[str] | str) -> IAssetInput:
        from rapidata.api_client.models.i_asset_input import IAssetInput
        from rapidata.api_client.models.i_asset_input_existing_asset_input import (
            IAssetInputExistingAssetInput,
        )
        from rapidata.api_client.models.i_asset_input_multi_asset_input import (
            IAssetInputMultiAssetInput,
        )

        if isinstance(assets, list):
            return IAssetInput(
                actual_instance=IAssetInputMultiAssetInput(
                    _t="MultiAssetInput",
                    assets=[
                        IAssetInput(
                            actual_instance=IAssetInputExistingAssetInput(
                                _t="ExistingAssetInput",
                                name=self.upload_asset(asset),
                            )
                        )
                        for asset in assets
                    ],
                )
            )
        else:
            return IAssetInput(
                actual_instance=IAssetInputExistingAssetInput(
                    _t="ExistingAssetInput",
                    name=self.upload_asset(assets),
                )
            )

    def clear_cache(self):
        self._shared_upload_cache.clear()
        logger.info("Upload cache cleared")

    def __str__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"

    def __repr__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"
