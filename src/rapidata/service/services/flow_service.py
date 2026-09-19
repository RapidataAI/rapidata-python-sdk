from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.flow_api import FlowApi
    from rapidata.api_client.api.ranking_flow_api import RankingFlowApi
    from rapidata.api_client.api.ranking_flow_item_api import RankingFlowItemApi
    from rapidata.api_client.api.simple_flow_api import SimpleFlowApi
    from rapidata.api_client.api.simple_flow_item_api import SimpleFlowItemApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class FlowService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._flow_api: FlowApi | None = None
        self._ranking_flow_api: RankingFlowApi | None = None
        self._ranking_flow_item_api: RankingFlowItemApi | None = None
        self._simple_flow_api: SimpleFlowApi | None = None
        self._simple_flow_item_api: SimpleFlowItemApi | None = None

    @property
    def flow_api(self) -> FlowApi:
        if self._flow_api is None:
            from rapidata.api_client.api.flow_api import FlowApi
            self._flow_api = FlowApi(self._api_client)
        return self._flow_api

    @property
    def ranking_flow_api(self) -> RankingFlowApi:
        if self._ranking_flow_api is None:
            from rapidata.api_client.api.ranking_flow_api import RankingFlowApi
            self._ranking_flow_api = RankingFlowApi(self._api_client)
        return self._ranking_flow_api

    @property
    def ranking_flow_item_api(self) -> RankingFlowItemApi:
        if self._ranking_flow_item_api is None:
            from rapidata.api_client.api.ranking_flow_item_api import RankingFlowItemApi
            self._ranking_flow_item_api = RankingFlowItemApi(self._api_client)
        return self._ranking_flow_item_api

    @property
    def simple_flow_api(self) -> SimpleFlowApi:
        if self._simple_flow_api is None:
            from rapidata.api_client.api.simple_flow_api import SimpleFlowApi
            self._simple_flow_api = SimpleFlowApi(self._api_client)
        return self._simple_flow_api

    @property
    def simple_flow_item_api(self) -> SimpleFlowItemApi:
        if self._simple_flow_item_api is None:
            from rapidata.api_client.api.simple_flow_item_api import SimpleFlowItemApi
            self._simple_flow_item_api = SimpleFlowItemApi(self._api_client)
        return self._simple_flow_item_api
