from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, TYPE_CHECKING

from tqdm.auto import tqdm

from rapidata.rapidata_client.config import logger, rapidata_config
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._batch_asset_uploader import (
    BatchAssetUploader,
)
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.datapoints._single_flight_cache import SingleFlightCache

if TYPE_CHECKING:
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint
    from rapidata.service.openapi_service import OpenAPIService


def extract_assets_from_datapoint(datapoint: Datapoint) -> set[str]:
    """
    Extract all assets from a single datapoint.

    Args:
        datapoint: The datapoint to extract assets from.

    Returns:
        Set of asset identifiers (URLs or file paths).
    """
    assets: set[str] = set()

    # Main asset(s)
    if isinstance(datapoint.asset, list):
        assets.update(datapoint.asset)
    else:
        assets.add(datapoint.asset)

    # Context asset
    if datapoint.media_context:
        assets.add(datapoint.media_context)

    return assets


class AssetUploadOrchestrator:
    """
    Orchestrates Step 1/2: Upload ALL assets from ALL datapoints.

    This class extracts all unique assets, separates URLs from files,
    filters cached assets, and uploads uncached assets using batch
    upload for URLs and parallel upload for files.

    Returns list of failed uploads for any assets that fail.
    """

    def __init__(self, openapi_service: OpenAPIService) -> None:
        self.asset_uploader = AssetUploader(openapi_service)
        self.batch_uploader = BatchAssetUploader(openapi_service)

    def upload_all_assets(
        self,
        assets: set[str] | list[str],
        asset_completion_callback: Callable[[list[str]], None] | None = None,
    ) -> list[FailedUpload[str]]:
        """
        Step 1/2: Upload ALL assets.
        Returns list of failed uploads for any assets that fail.

        Args:
            assets: Set or list of asset identifiers (URLs or file paths) to upload.
            asset_completion_callback: Optional callback to notify when assets complete (called with list of successful assets).

        Returns:
            List of FailedUpload instances for any assets that failed.
        """
        # 1. Validate assets
        all_assets = set(assets) if isinstance(assets, list) else assets
        logger.info(f"Uploading {len(all_assets)} unique asset(s)")

        if not all_assets:
            logger.debug("No assets to upload")
            return []

        # 2. Separate and filter assets
        urls, files = self._separate_urls_and_files(all_assets)
        uncached_urls, uncached_files = self._filter_and_log_cached_assets(urls, files)

        # Notify callback about cached assets (already complete)
        cached_assets = []
        if uncached_urls:
            cached_assets.extend(urls - uncached_urls)
        if uncached_files:
            cached_assets.extend(files - uncached_files)

        if cached_assets and asset_completion_callback:
            logger.debug(f"Notifying callback of {len(cached_assets)} cached asset(s)")
            asset_completion_callback(cached_assets)

        if len(uncached_urls) + len(uncached_files) == 0:
            logger.debug("All assets cached, nothing to upload")
            return []

        # 3. Perform uploads
        failed_uploads = self._perform_uploads(
            uncached_urls, uncached_files, asset_completion_callback
        )

        # 4. Report results
        self._log_upload_results(failed_uploads)
        return failed_uploads

    def _separate_urls_and_files(self, assets: set[str]) -> tuple[set[str], set[str]]:
        """
        Separate assets into URLs and file paths.

        Args:
            assets: Set of asset identifiers.

        Returns:
            Tuple of (urls, files).
        """
        urls = {a for a in assets if re.match(r"^https?://", a)}
        files = {a for a in assets if not re.match(r"^https?://", a)}
        logger.debug(f"Asset breakdown: {len(urls)} URL(s), {len(files)} file(s)")
        return urls, files

    def _filter_and_log_cached_assets(
        self, urls: set[str], files: set[str]
    ) -> tuple[set[str], set[str]]:
        """
        Filter out cached assets and log statistics.

        Args:
            urls: Set of URL assets.
            files: Set of file assets.

        Returns:
            Tuple of (uncached_urls, uncached_files).
        """
        uncached_urls = self._filter_uncached(urls, self.asset_uploader._url_cache)
        uncached_files = self._filter_uncached(
            files, self.asset_uploader._get_file_cache()
        )

        logger.info(
            f"Assets to upload: {len(uncached_urls)} URL(s), {len(uncached_files)} file(s) "
            f"(skipped {len(urls) - len(uncached_urls)} cached URL(s), "
            f"{len(files) - len(uncached_files)} cached file(s))"
        )

        return uncached_urls, uncached_files

    def _perform_uploads(
        self,
        uncached_urls: set[str],
        uncached_files: set[str],
        asset_completion_callback: Callable[[list[str]], None] | None,
    ) -> list[FailedUpload[str]]:
        """
        Execute asset uploads with progress tracking.

        Args:
            uncached_urls: URLs to upload.
            uncached_files: Files to upload.
            asset_completion_callback: Callback for completed assets.

        Returns:
            List of failed uploads.
        """
        failed_uploads: list[FailedUpload[str]] = []
        total = len(uncached_urls) + len(uncached_files)

        with tqdm(
            total=total,
            desc="Step 1/2: Uploading assets",
            position=0,
            disable=rapidata_config.logging.silent_mode,
            leave=True,
        ) as pbar:
            # Upload URLs
            if uncached_urls:
                url_failures = self._upload_urls_with_progress(
                    uncached_urls, pbar, asset_completion_callback
                )
                failed_uploads.extend(url_failures)
            else:
                logger.debug("No uncached URLs to upload")

            # Upload files
            if uncached_files:
                file_failures = self._upload_files_with_progress(
                    uncached_files, pbar, asset_completion_callback
                )
                failed_uploads.extend(file_failures)
            else:
                logger.debug("No uncached files to upload")

        return failed_uploads

    def _upload_urls_with_progress(
        self,
        urls: set[str],
        pbar: tqdm,
        completion_callback: Callable[[list[str]], None] | None,
    ) -> list[FailedUpload[str]]:
        """Upload URLs with progress bar updates."""
        logger.debug(f"Batch uploading {len(urls)} URL(s)")

        def update_progress(n: int) -> None:
            pbar.update(n)

        return self.batch_uploader.batch_upload_urls(
            list(urls),
            progress_callback=update_progress,
            completion_callback=completion_callback,
        )

    def _upload_files_with_progress(
        self,
        files: set[str],
        pbar: tqdm,
        completion_callback: Callable[[list[str]], None] | None,
    ) -> list[FailedUpload[str]]:
        """Upload files with progress bar updates."""
        logger.debug(f"Parallel uploading {len(files)} file(s)")

        def update_progress() -> None:
            pbar.update(1)

        return self._upload_files_parallel(
            files,
            progress_callback=update_progress,
            completion_callback=completion_callback,
        )

    def _log_upload_results(self, failed_uploads: list[FailedUpload[str]]) -> None:
        """Log the results of asset uploads."""
        if failed_uploads:
            logger.warning(f"Step 1/2: {len(failed_uploads)} asset(s) failed to upload")
        else:
            logger.info("Step 1/2: All assets uploaded successfully")

    def _filter_uncached(self, assets: set[str], cache: SingleFlightCache) -> set[str]:
        """Filter out assets that are already cached."""
        uncached = set()
        for asset in assets:
            try:
                # Try to get cache key using centralized methods
                if re.match(r"^https?://", asset):
                    cache_key = self.asset_uploader.get_url_cache_key(asset)
                else:
                    cache_key = self.asset_uploader.get_file_cache_key(asset)

                # Check if in cache
                if cache_key not in cache.get_storage():
                    uncached.add(asset)
            except Exception as e:
                # If cache check fails, include in upload list
                logger.warning(f"Cache check failed for {asset}: {e}")
                uncached.add(asset)

        return uncached

    def _upload_files_parallel(
        self,
        files: set[str],
        progress_callback: Callable[[], None] | None = None,
        completion_callback: Callable[[list[str]], None] | None = None,
    ) -> list[FailedUpload[str]]:
        """
        Upload files in parallel using ThreadPoolExecutor.

        Args:
            files: Set of file paths to upload.
            progress_callback: Optional callback to report progress (called once per completed file).
            completion_callback: Optional callback to notify when files complete (called with list of successful files).

        Returns:
            List of FailedUpload instances for any files that failed.
        """
        failed_uploads: list[FailedUpload[str]] = []

        def upload_single_file(file_path: str) -> FailedUpload[str] | None:
            """Upload a single file and return FailedUpload if it fails."""
            try:
                self.asset_uploader.upload_asset(file_path)
                return None
            except Exception as e:
                logger.warning(f"Failed to upload file {file_path}: {e}")
                return FailedUpload.from_exception(file_path, e)

        with ThreadPoolExecutor(
            max_workers=rapidata_config.upload.maxWorkers
        ) as executor:
            futures = {
                executor.submit(upload_single_file, file_path): file_path
                for file_path in files
            }

            for future in as_completed(futures):
                file_path = futures[future]
                result = future.result()
                if result is not None:
                    failed_uploads.append(result)
                else:
                    # File uploaded successfully, notify callback
                    if completion_callback:
                        completion_callback([file_path])

                if progress_callback:
                    progress_callback()

        return failed_uploads
