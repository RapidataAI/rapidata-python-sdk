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
from rapidata.rapidata_client.exceptions.asset_upload_exception import (
    AssetUploadException,
)
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload

if TYPE_CHECKING:
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint
    from rapidata.service.openapi_service import OpenAPIService


class AssetUploadOrchestrator:
    """
    Orchestrates Step 1/2: Upload ALL assets from ALL datapoints.

    This class extracts all unique assets, separates URLs from files,
    filters cached assets, and uploads uncached assets using batch
    upload for URLs and parallel upload for files.

    Raises AssetUploadException if any uploads fail.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self.asset_uploader = AssetUploader(openapi_service)
        self.batch_uploader = BatchAssetUploader(openapi_service)

    def upload_all_assets(self, datapoints: list[Datapoint]) -> None:
        """
        Step 1/2: Upload ALL assets from ALL datapoints.
        Throws AssetUploadException if any uploads fail.

        Args:
            datapoints: List of datapoints to extract assets from.

        Raises:
            AssetUploadException: If any asset uploads fail.
        """
        # 1. Extract all unique assets (deduplicate)
        all_assets = self._extract_unique_assets(datapoints)
        logger.info(f"Extracted {len(all_assets)} unique asset(s) from datapoints")

        if not all_assets:
            logger.debug("No assets to upload")
            return

        # 2. Separate URLs vs files
        urls = [a for a in all_assets if re.match(r"^https?://", a)]
        files = [a for a in all_assets if not re.match(r"^https?://", a)]
        logger.debug(f"Asset breakdown: {len(urls)} URL(s), {len(files)} file(s)")

        # 3. Filter cached (skip already-uploaded assets)
        uncached_urls = self._filter_uncached(urls, self.asset_uploader._url_cache)
        uncached_files = self._filter_uncached(files, self.asset_uploader._file_cache)
        logger.info(
            f"Assets to upload: {len(uncached_urls)} URL(s), {len(uncached_files)} file(s) "
            f"(skipped {len(urls) - len(uncached_urls)} cached URL(s), "
            f"{len(files) - len(uncached_files)} cached file(s))"
        )

        total = len(uncached_urls) + len(uncached_files)
        if total == 0:
            logger.debug("All assets cached, nothing to upload")
            return

        # 4. Upload with single progress bar
        failed_uploads: list[FailedUpload[str]] = []
        with tqdm(
            total=total,
            desc="Step 1/2: Uploading assets",
            disable=rapidata_config.logging.silent_mode,
        ) as pbar:
            # 4a. Batch upload URLs
            if uncached_urls:
                logger.debug(f"Batch uploading {len(uncached_urls)} URL(s)")

                def update_progress(n: int) -> None:
                    pbar.update(n)

                url_failures = self.batch_uploader.batch_upload_urls(
                    uncached_urls, progress_callback=update_progress
                )
                failed_uploads.extend(url_failures)
            else:
                logger.debug("No uncached URLs to upload")

            # 4b. Parallel upload files
            if uncached_files:
                logger.debug(f"Parallel uploading {len(uncached_files)} file(s)")

                def update_file_progress() -> None:
                    pbar.update(1)

                file_failures = self._upload_files_parallel(
                    uncached_files, progress_callback=update_file_progress
                )
                failed_uploads.extend(file_failures)
            else:
                logger.debug("No uncached files to upload")

        # 5. If any failures, throw exception (before Step 2)
        if failed_uploads:
            logger.error(
                f"Asset upload failed for {len(failed_uploads)} asset(s) in Step 1/2"
            )
            raise AssetUploadException(failed_uploads)

        logger.info("Step 1/2: All assets uploaded successfully")

    def _extract_unique_assets(self, datapoints: list[Datapoint]) -> set[str]:
        """Extract all unique assets from all datapoints."""
        assets: set[str] = set()
        for dp in datapoints:
            # Main asset(s)
            if isinstance(dp.asset, list):
                assets.update(dp.asset)
            else:
                assets.add(dp.asset)
            # Context asset
            if dp.media_context:
                assets.add(dp.media_context)
        return assets

    def _filter_uncached(self, assets: list[str], cache) -> list[str]:
        """Filter out assets that are already cached."""
        uncached = []
        for asset in assets:
            try:
                # Try to get cache key
                if re.match(r"^https?://", asset):
                    cache_key = (
                        f"{self.asset_uploader.openapi_service.environment}@{asset}"
                    )
                else:
                    cache_key = self.asset_uploader._get_file_cache_key(asset)

                # Check if in cache
                if cache_key not in cache._storage:
                    uncached.append(asset)
            except Exception as e:
                # If cache check fails, include in upload list
                logger.debug(f"Cache check failed for {asset}: {e}")
                uncached.append(asset)

        return uncached

    def _upload_files_parallel(
        self,
        files: list[str],
        progress_callback: Callable[[], None] | None = None,
    ) -> list[FailedUpload[str]]:
        """
        Upload files in parallel using ThreadPoolExecutor.

        Args:
            files: List of file paths to upload.
            progress_callback: Optional callback to report progress (called once per completed file).

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
                result = future.result()
                if result is not None:
                    failed_uploads.append(result)

                if progress_callback:
                    progress_callback()

        return failed_uploads
