from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.pipeline_api import PipelineApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class PipelineService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._pipeline_api: PipelineApi | None = None

    @property
    def pipeline_api(self) -> PipelineApi:
        if self._pipeline_api is None:
            from rapidata.api_client.api.pipeline_api import PipelineApi
            self._pipeline_api = PipelineApi(self._api_client)
        return self._pipeline_api
