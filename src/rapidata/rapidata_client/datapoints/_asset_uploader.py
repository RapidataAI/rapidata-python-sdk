from __future__ import annotations

import re
import os
from typing import TYPE_CHECKING

from rapidata.rapidata_client.config.upload_config import (
    register_upload_config_handler,
    UploadConfig,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, rapidata_config, tracer
from rapidata.rapidata_client.datapoints._single_flight_cache import SingleFlightCache
from diskcache import FanoutCache

if TYPE_CHECKING:
    from rapidata.api_client.models.i_asset_input import IAssetInput


class AssetUploader:
    _file_cache: SingleFlightCache = SingleFlightCache(
        "File cache",
        storage=FanoutCache(
            rapidata_config.upload.cacheLocation,
            shards=rapidata_config.upload.maxWorkers,
            timeout=rapidata_config.upload.cacheTimeout,
            size_limit=rapidata_config.upload.cacheSizeLimit,
        ),
    )
    _url_cache: SingleFlightCache = SingleFlightCache("URL cache")

    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        register_upload_config_handler(self._handle_config_update)

    @classmethod
    def _handle_config_update(cls, config: UploadConfig):
        """Handle updates to the upload config by re-creating the file cache storage."""
        logger.debug("Updating AssetUploader file cache with new config")
        try:
            cls._file_cache.set_storage(
                FanoutCache(
                    config.cacheLocation,
                    shards=config.maxWorkers,
                    timeout=config.cacheTimeout,
                    size_limit=config.cacheSizeLimit,
                )
            )
            logger.info(
                "AssetUploader file cache updated: location=%s, shards=%s, timeout=%s, size_limit=%s",
                config.cacheLocation,
                config.maxWorkers,
                config.cacheTimeout,
                config.cacheSizeLimit,
            )
        except Exception as e:
            logger.warning(f"Failed to update AssetUploader file cache: {e}")

    def _get_file_cache_key(self, asset: str) -> str:
        """Generate cache key for a file, including environment."""
        env = self.openapi_service.environment
        if not os.path.exists(asset):
            raise FileNotFoundError(f"File not found: {asset}")

        stat = os.stat(asset)
        return f"{env}@{asset}:{stat.st_size}:{stat.st_mtime_ns}"

    def _get_url_cache_key(self, url: str) -> str:
        """Generate cache key for a URL, including environment."""
        env = self.openapi_service.environment
        return f"{env}@{url}"

    def _upload_url_asset(self, url: str) -> str:
        """Upload a URL asset, with optional caching."""

        def upload_url() -> str:
            response = self.openapi_service.asset_api.asset_url_post(url=url)
            logger.info(
                "Asset uploaded from URL: %s, file name: %s", url, response.file_name
            )
            return response.file_name

        if not rapidata_config.upload.cacheUploads:
            return upload_url()

        return self._url_cache.get_or_fetch(
            self._get_url_cache_key(url),
            upload_url,
            should_cache=rapidata_config.upload.cacheUploads,
        )

    def _upload_file_asset(self, file_path: str) -> str:
        """Upload a local file asset, with optional caching."""

        def upload_file() -> str:
            response = self.openapi_service.asset_api.asset_file_post(file=file_path)
            logger.info(
                "Asset uploaded from file: %s, file name: %s",
                file_path,
                response.file_name,
            )
            return response.file_name

        if not rapidata_config.upload.cacheUploads:
            return upload_file()

        return self._file_cache.get_or_fetch(
            self._get_file_cache_key(file_path),
            upload_file,
            should_cache=rapidata_config.upload.cacheUploads,
        )

    def upload_asset(self, asset: str) -> str:
        with tracer.start_as_current_span("AssetUploader.upload_asset"):
            logger.debug("Uploading asset: %s", asset)
            assert isinstance(asset, str), "Asset must be a string"

            if re.match(r"^https?://", asset):
                return self._upload_url_asset(asset)

            return self._upload_file_asset(asset)

    def clear_cache(self):
        self._file_cache.clear()
        self._url_cache.clear()
        logger.info("Upload cache cleared")

    def __str__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"

    def __repr__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"
