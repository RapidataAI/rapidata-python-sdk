from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.customer_rapid_api import CustomerRapidApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class RapidService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._rapid_api: CustomerRapidApi | None = None

    @property
    def rapid_api(self) -> CustomerRapidApi:
        if self._rapid_api is None:
            from rapidata.api_client.api.customer_rapid_api import CustomerRapidApi
            self._rapid_api = CustomerRapidApi(self._api_client)
        return self._rapid_api
