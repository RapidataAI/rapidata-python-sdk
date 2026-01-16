from __future__ import annotations

import re
import os
import threading
from concurrent.futures import Future
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
    _url_memory_cache: dict[str, str] = {}
    _url_in_flight: dict[str, Future[str]] = {}
    _url_cache_lock: threading.Lock = threading.Lock()
    _file_in_flight: dict[str, Future[str]] = {}
    _file_cache_lock: threading.Lock = threading.Lock()

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

    def _get_url_cache_key(self, url: str) -> str:
        """Generate cache key for a URL, including environment."""
        env = self.openapi_service.environment
        return f"{env}@{url}"

    def upload_asset(self, asset: str) -> str:
        with tracer.start_as_current_span("AssetUploader.upload_asset"):
            logger.debug("Uploading asset: %s", asset)
            assert isinstance(asset, str), "Asset must be a string"
            if re.match(r"^https?://", asset):
                url_key = self._get_url_cache_key(asset)

                # Fast path - check cache without lock
                cached_value = self._url_memory_cache.get(url_key)
                if cached_value is not None:
                    logger.debug("URL found in memory cache")
                    return cached_value

                with self._url_cache_lock:
                    # Double-check cache under lock
                    cached_value = self._url_memory_cache.get(url_key)
                    if cached_value is not None:
                        logger.debug("URL found in memory cache")
                        return cached_value

                    # Check if there's an in-flight request for this URL
                    in_flight = self._url_in_flight.get(url_key)
                    if in_flight is None:
                        # We're the first - create a future
                        in_flight = Future()
                        self._url_in_flight[url_key] = in_flight
                        should_fetch = True
                    else:
                        should_fetch = False

                if not should_fetch:
                    logger.debug("URL upload already in flight, waiting...")
                    return in_flight.result()

                # We need to fetch
                try:
                    response = self.openapi_service.asset_api.asset_url_post(
                        url=asset,
                    )
                    result = response.file_name
                    self._url_memory_cache[url_key] = result
                    in_flight.set_result(result)
                    logger.debug("URL added to memory cache")
                    return result
                except Exception as e:
                    in_flight.set_exception(e)
                    raise
                finally:
                    with self._url_cache_lock:
                        self._url_in_flight.pop(url_key, None)

            asset_key = self._get_cache_key(asset)

            # Fast path - check cache without lock
            cached_value = self._shared_upload_cache.get(asset_key)
            if cached_value is not None:
                logger.debug("Asset found in cache")
                return cast(str, cached_value)

            with self._file_cache_lock:
                # Double-check cache under lock
                cached_value = self._shared_upload_cache.get(asset_key)
                if cached_value is not None:
                    logger.debug("Asset found in cache")
                    return cast(str, cached_value)

                # Check if there's an in-flight upload for this file
                in_flight = self._file_in_flight.get(asset_key)
                if in_flight is None:
                    # We're the first - create a future
                    in_flight = Future()
                    self._file_in_flight[asset_key] = in_flight
                    should_upload = True
                else:
                    should_upload = False

            if not should_upload:
                logger.debug("File upload already in flight, waiting...")
                return in_flight.result()

            # We need to upload
            try:
                response = self.openapi_service.asset_api.asset_file_post(
                    file=asset,
                )
                result = response.file_name
                if rapidata_config.upload.cacheUploads:
                    self._shared_upload_cache[asset_key] = result
                    logger.debug("Asset added to cache")
                in_flight.set_result(result)
                logger.info("Asset uploaded: %s", result)
                return result
            except Exception as e:
                in_flight.set_exception(e)
                raise
            finally:
                with self._file_cache_lock:
                    self._file_in_flight.pop(asset_key, None)

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
        self._url_memory_cache.clear()
        logger.info("Upload cache cleared")

    def __str__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"

    def __repr__(self) -> str:
        return f"AssetUploader(openapi_service={self.openapi_service})"
