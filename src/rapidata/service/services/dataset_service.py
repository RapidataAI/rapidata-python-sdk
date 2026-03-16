from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.dataset_api import DatasetApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class DatasetService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._dataset_api: DatasetApi | None = None

    @property
    def dataset_api(self) -> DatasetApi:
        if self._dataset_api is None:
            from rapidata.api_client.api.dataset_api import DatasetApi
            self._dataset_api = DatasetApi(self._api_client)
        return self._dataset_api
