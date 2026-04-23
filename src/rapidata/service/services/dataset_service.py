from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from rapidata.api_client.api.dataset_api import DatasetApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient
    from rapidata.api_client.api.dataset_group_api import DatasetGroupApi
    from rapidata.api_client.api.datapoints_api import DatapointsApi


class DatasetService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._dataset_api: DatasetApi | None = None
        self._dataset_group_api: DatasetGroupApi | None = None
        self._datapoints_api: DatapointsApi | None = None

    @property
    def dataset_api(self) -> DatasetApi:
        if self._dataset_api is None:
            from rapidata.api_client.api.dataset_api import DatasetApi

            self._dataset_api = DatasetApi(self._api_client)
        return self._dataset_api

    @property
    def dataset_group_api(self) -> DatasetGroupApi:
        if self._dataset_group_api is None:
            from rapidata.api_client.api.dataset_group_api import DatasetGroupApi

            self._dataset_group_api = DatasetGroupApi(self._api_client)
        return self._dataset_group_api

    @property
    def datapoints_api(self) -> DatapointsApi:
        if self._datapoints_api is None:
            from rapidata.api_client.api.datapoints_api import DatapointsApi

            self._datapoints_api = DatapointsApi(self._api_client)
        return self._datapoints_api
