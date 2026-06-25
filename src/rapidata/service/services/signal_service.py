from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.signal_api import SignalApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class SignalService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._signal_api: SignalApi | None = None

    @property
    def signal_api(self) -> SignalApi:
        if self._signal_api is None:
            from rapidata.api_client.api.signal_api import SignalApi
            self._signal_api = SignalApi(self._api_client)
        return self._signal_api
