from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.campaign_api import CampaignApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class CampaignService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._campaign_api: CampaignApi | None = None

    @property
    def campaign_api(self) -> CampaignApi:
        if self._campaign_api is None:
            from rapidata.api_client.api.campaign_api import CampaignApi
            self._campaign_api = CampaignApi(self._api_client)
        return self._campaign_api
