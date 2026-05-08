from __future__ import annotations

import re
import os
import threading
from typing import Any

from rapidata.api_client.models.i_asset_input import IAssetInput
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, rapidata_config, tracer
from rapidata.rapidata_client.config.upload_config import CompressionConfig
from rapidata.rapidata_client.datapoints._asset_mapper import AssetMapper
from rapidata.rapidata_client.datapoints._single_flight_cache import SingleFlightCache
from diskcache import FanoutCache


def _compression_kwargs(compression: CompressionConfig | None) -> dict[str, Any]:
    """
    Build the kwargs dict to pass to the OpenAPI upload methods. Only includes
    fields the user explicitly set so the call shape is unchanged when
    compression is disabled — keeping us forward-compatible with older
    OpenAPI clients that don't yet expose the params.
    """
    if compression is None or not compression.is_set():
        return {}
    kwargs: dict[str, Any] = {}
    if compression.enabled is not None:
        kwargs["compress"] = compression.enabled
    if compression.quality is not None:
        kwargs["quality"] = compression.quality
    if compression.max_dimension is not None:
        kwargs["maxdim"] = compression.max_dimension
    if compression.library is not None:
        kwargs["library"] = compression.library
    return kwargs


class AssetUploader:
    # Class-level caches shared across all instances
    # URL cache: Always in-memory (URLs are lightweight, no benefit to disk caching)
    # File cache: Lazily initialized based on cacheToDisk config
    _url_cache: SingleFlightCache = SingleFlightCache("URL cache", storage={})
    _file_cache: SingleFlightCache | None = None
    _file_cache_uses_disk: bool | None = None
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
        cache_to_disk = rapidata_config.upload.cacheToDisk

        if cls._file_cache is not None and cls._file_cache_uses_disk == cache_to_disk:
            return cls._file_cache

        with cls._file_cache_lock:
            # Double-check after acquiring lock
            if (
                cls._file_cache is not None
                and cls._file_cache_uses_disk == cache_to_disk
            ):
                return cls._file_cache

            # Create cache storage based on current config
            if cache_to_disk:
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
            cls._file_cache_uses_disk = cache_to_disk
            return cls._file_cache

    def __init__(self, openapi_service: OpenAPIService) -> None:
        self.openapi_service = openapi_service

    def get_file_cache_key(self, asset: str) -> str:
        """Generate cache key for a file, including environment and active compression settings."""
        env = self.openapi_service.environment
        try:
            stat = os.stat(asset)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {asset}") from None
        suffix = self._compression_cache_suffix()
        return f"{env}@{asset}:{stat.st_size}:{stat.st_mtime_ns}{suffix}"

    def get_url_cache_key(self, url: str) -> str:
        """Generate cache key for a URL, including environment and active compression settings."""
        env = self.openapi_service.environment
        return f"{env}@{url}{self._compression_cache_suffix()}"

    @staticmethod
    def _compression_cache_suffix() -> str:
        compression = rapidata_config.upload.compression
        return compression.cache_suffix() if compression is not None else ""

    def _upload_url_asset(self, url: str) -> str:
        """
        Upload a URL asset with caching.

        URLs are always cached in-memory (lightweight, no disk I/O overhead).
        Caching is required for the two-step upload flow and cannot be disabled.
        """

        kwargs = _compression_kwargs(rapidata_config.upload.compression)

        def upload_url() -> str:
            response = self.openapi_service.asset.asset_api.asset_url_post(
                url=url, **kwargs
            )
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

        kwargs = _compression_kwargs(rapidata_config.upload.compression)

        def upload_file() -> str:
            response = self.openapi_service.asset.asset_api.asset_file_post(
                file=file_path, **kwargs
            )
            logger.info(
                "Asset uploaded from file: %s, file name: %s",
                file_path,
                response.file_name,
            )
            return response.file_name

        return self._get_file_cache().get_or_fetch(
            self.get_file_cache_key(file_path), upload_file
        )

    # Accept http / https / HTTP / HTTPS / mixed case — people type URLs
    # by hand or copy them from docs with varying capitalisation.
    _URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)

    def upload_asset(self, asset: str) -> str:
        logger.debug("Uploading asset: %s", asset)
        if not isinstance(asset, str):
            raise TypeError(
                f"Asset must be a string, got {type(asset).__name__}"
            )

        if self._URL_SCHEME_RE.match(asset):
            return self._upload_url_asset(asset)

        return self._upload_file_asset(asset)

    def upload_and_map_asset(self, asset: str | list[str]) -> IAssetInput:
        """Upload asset(s) and wrap the result in an ``IAssetInput``.

        Used both for main datapoint/example assets and for ``media_context``.
        A single string is returned as a plain ``ExistingAssetInput``; a list
        is bundled into a ``MultiAssetInput``.
        """
        if isinstance(asset, list):
            uploaded_names = [self.upload_asset(a) for a in asset]
            return AssetMapper.create_existing_asset_input(uploaded_names)

        return AssetMapper.create_existing_asset_input(self.upload_asset(asset))

    def clear_cache(self) -> None:
        """Clear both URL and file caches."""
        self._get_file_cache().clear()
        self._url_cache.clear()
        logger.info("Upload cache cleared")

    def __str__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"

    def __repr__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"
