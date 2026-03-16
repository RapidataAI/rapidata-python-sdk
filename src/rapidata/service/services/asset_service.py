from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.asset_api import AssetApi
    from rapidata.api_client.api.batch_upload_api import BatchUploadApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class AssetService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._asset_api: AssetApi | None = None
        self._batch_upload_api: BatchUploadApi | None = None

    @property
    def asset_api(self) -> AssetApi:
        if self._asset_api is None:
            from rapidata.api_client.api.asset_api import AssetApi
            self._asset_api = AssetApi(self._api_client)
        return self._asset_api

    @property
    def batch_upload_api(self) -> BatchUploadApi:
        if self._batch_upload_api is None:
            from rapidata.api_client.api.batch_upload_api import BatchUploadApi
            self._batch_upload_api = BatchUploadApi(self._api_client)
        return self._batch_upload_api
