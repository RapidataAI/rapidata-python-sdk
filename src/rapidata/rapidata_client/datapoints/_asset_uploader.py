from __future__ import annotations

import re
import os
import threading
from typing import TYPE_CHECKING

from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, rapidata_config, tracer
from rapidata.rapidata_client.datapoints._single_flight_cache import SingleFlightCache
from diskcache import FanoutCache

if TYPE_CHECKING:
    from rapidata.api_client.models.i_asset_input import IAssetInput


class AssetUploader:
    # Class-level caches shared across all instances
    # URL cache: Always in-memory (URLs are lightweight, no benefit to disk caching)
    # File cache: Lazily initialized based on cacheToDisk config
    _url_cache: SingleFlightCache = SingleFlightCache("URL cache", storage={})
    _file_cache: SingleFlightCache | None = None
    _file_cache_lock: threading.Lock = threading.Lock()

    @classmethod
    def _get_file_cache(cls) -> SingleFlightCache:
        """
        Get or create the file cache based on current config.

        Uses lazy initialization to respect cacheToDisk setting at runtime.
        Thread-safe with double-checked locking pattern.

        Returns:
            Configured file cache (disk or memory based on cacheToDisk).
        """
        if cls._file_cache is not None:
            return cls._file_cache

        with cls._file_cache_lock:
            # Double-check after acquiring lock
            if cls._file_cache is not None:
                return cls._file_cache

            # Create cache storage based on current config
            if rapidata_config.upload.cacheToDisk:
                storage: dict[str, str] | FanoutCache = FanoutCache(
                    rapidata_config.upload.cacheLocation,
                    shards=rapidata_config.upload.cacheShards,
                    timeout=rapidata_config.upload.cacheTimeout,
                )
                logger.debug("Initialized file cache with disk storage")
            else:
                storage = {}
                logger.debug("Initialized file cache with in-memory storage")

            cls._file_cache = SingleFlightCache("File cache", storage=storage)
            return cls._file_cache

    def __init__(self, openapi_service: OpenAPIService) -> None:
        self.openapi_service = openapi_service

    def get_file_cache_key(self, asset: str) -> str:
        """Generate cache key for a file, including environment."""
        env = self.openapi_service.environment
        if not os.path.exists(asset):
            raise FileNotFoundError(f"File not found: {asset}")

        stat = os.stat(asset)
        return f"{env}@{asset}:{stat.st_size}:{stat.st_mtime_ns}"

    def get_url_cache_key(self, url: str) -> str:
        """Generate cache key for a URL, including environment."""
        env = self.openapi_service.environment
        return f"{env}@{url}"

    def _upload_url_asset(self, url: str) -> str:
        """
        Upload a URL asset with caching.

        URLs are always cached in-memory (lightweight, no disk I/O overhead).
        Caching is required for the two-step upload flow and cannot be disabled.
        """

        def upload_url() -> str:
            response = self.openapi_service.asset_api.asset_url_post(url=url)
            logger.info(
                "Asset uploaded from URL: %s, file name: %s", url, response.file_name
            )
            return response.file_name

        return self._url_cache.get_or_fetch(self.get_url_cache_key(url), upload_url)

    def _upload_file_asset(self, file_path: str) -> str:
        """
        Upload a local file asset with caching.

        Caching is always enabled as it's required for the two-step upload flow.
        Use cacheToDisk config to control whether cache is stored to disk or memory.
        """

        def upload_file() -> str:
            response = self.openapi_service.asset_api.asset_file_post(file=file_path)
            logger.info(
                "Asset uploaded from file: %s, file name: %s",
                file_path,
                response.file_name,
            )
            return response.file_name

        return self._get_file_cache().get_or_fetch(
            self.get_file_cache_key(file_path), upload_file
        )

    def upload_asset(self, asset: str) -> str:
        with tracer.start_as_current_span("AssetUploader.upload_asset"):
            logger.debug("Uploading asset: %s", asset)
            assert isinstance(asset, str), "Asset must be a string"

            if re.match(r"^https?://", asset):
                return self._upload_url_asset(asset)

            return self._upload_file_asset(asset)

    def clear_cache(self) -> None:
        """Clear both URL and file caches."""
        self._get_file_cache().clear()
        self._url_cache.clear()
        logger.info("Upload cache cleared")

    def __str__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"

    def __repr__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"
