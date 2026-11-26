from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.auto_top_up_api import AutoTopUpApi
    from rapidata.api_client.api.billing_api import BillingApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class PaymentService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._billing_api: BillingApi | None = None
        self._auto_top_up_api: AutoTopUpApi | None = None

    @property
    def billing_api(self) -> BillingApi:
        if self._billing_api is None:
            from rapidata.api_client.api.billing_api import BillingApi
            self._billing_api = BillingApi(self._api_client)
        return self._billing_api

    @property
    def auto_top_up_api(self) -> AutoTopUpApi:
        if self._auto_top_up_api is None:
            from rapidata.api_client.api.auto_top_up_api import AutoTopUpApi
            self._auto_top_up_api = AutoTopUpApi(self._api_client)
        return self._auto_top_up_api
