from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.api.workflow_api import WorkflowApi
    from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient


class WorkflowService:
    def __init__(self, api_client: RapidataApiClient) -> None:
        self._api_client = api_client
        self._workflow_api: WorkflowApi | None = None

    @property
    def workflow_api(self) -> WorkflowApi:
        if self._workflow_api is None:
            from rapidata.api_client.api.workflow_api import WorkflowApi
            self._workflow_api = WorkflowApi(self._api_client)
        return self._workflow_api
