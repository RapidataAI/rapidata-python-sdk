from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.order_api import OrderApi
    from rapidata.api_client.api.job_api import JobApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class OrderService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._order_api: OrderApi | None = None
        self._job_api: JobApi | None = None

    @property
    def order_api(self) -> OrderApi:
        if self._order_api is None:
            from rapidata.api_client.api.order_api import OrderApi
            self._order_api = OrderApi(self._api_client)
        return self._order_api

    @property
    def job_api(self) -> JobApi:
        if self._job_api is None:
            from rapidata.api_client.api.job_api import JobApi
            self._job_api = JobApi(self._api_client)
        return self._job_api
