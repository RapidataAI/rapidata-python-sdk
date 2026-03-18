from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.audience_api import AudienceApi
    from rapidata.api_client.api.examples_api import ExamplesApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class AudienceService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._audience_api: AudienceApi | None = None
        self._examples_api: ExamplesApi | None = None

    @property
    def audience_api(self) -> AudienceApi:
        if self._audience_api is None:
            from rapidata.api_client.api.audience_api import AudienceApi
            self._audience_api = AudienceApi(self._api_client)
        return self._audience_api

    @property
    def examples_api(self) -> ExamplesApi:
        if self._examples_api is None:
            from rapidata.api_client.api.examples_api import ExamplesApi
            self._examples_api = ExamplesApi(self._api_client)
        return self._examples_api
