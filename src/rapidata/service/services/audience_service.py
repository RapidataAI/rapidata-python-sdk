from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.audience_api import AudienceApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class AudienceService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._audience_api: AudienceApi | None = None

    @property
    def audience_api(self) -> AudienceApi:
        if self._audience_api is None:
            from rapidata.api_client.api.audience_api import AudienceApi
            self._audience_api = AudienceApi(self._api_client)
        return self._audience_api
