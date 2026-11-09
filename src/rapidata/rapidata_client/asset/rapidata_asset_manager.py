from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints.assets.uploaded_asset import UploadedAsset

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService


class RapidataAssetManager:
    """Upload media once and reuse the reference across job definitions.

    Access this manager via :py:attr:`RapidataClient.asset`.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._asset_uploader = AssetUploader(openapi_service)
        logger.debug("RapidataAssetManager initialized")

    def upload(self, asset: str) -> UploadedAsset:
        """Upload a local file or a URL and return a reference to it.

        Pass the reference as a datapoint or media context of any
        ``create_*_job_definition``; it is not uploaded again. Uploads share the
        SDK's upload cache, so uploading the same path or URL twice returns the
        same reference without a second upload.

        Args:
            asset (str): A local file path or an http(s) URL.

        Returns:
            UploadedAsset: The reference to the uploaded media.
        """
        with tracer.start_as_current_span("RapidataAssetManager.upload"):
            uploaded = UploadedAsset(self._asset_uploader.upload_asset(asset))
            for warning in self._asset_uploader.drain_warnings():
                logger.warning(
                    "Upload warning for '%s': %s", warning.item, warning.message
                )
            return uploaded

    def __str__(self) -> str:
        return "RapidataAssetManager"

    def __repr__(self) -> str:
        return self.__str__()
