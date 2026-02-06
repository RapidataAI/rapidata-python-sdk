from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer
from rapidata.service.openapi_service import OpenAPIService

if TYPE_CHECKING:
    from rapidata.api_client.models.flow_item_state import FlowItemState
    from rapidata.api_client.models.get_flow_item_by_id_endpoint_output import (
        GetFlowItemByIdEndpointOutput,
    )


class RapidataFlowItem:
    def __init__(self, id: str, flow_id: str, openapi_service: OpenAPIService):
        self.id = id
        self.flow_id = flow_id
        self._openapi_service = openapi_service

    def get_status(self) -> FlowItemState:
        """Get the current state of this flow item.

        Returns:
            FlowItemState: The current state (Pending, Running, Completed, Failed).
        """
        with tracer.start_as_current_span("RapidataFlowItem.get_status"):
            logger.debug("Getting status for flow item '%s'", self.id)
            details = self._get_details()
            return details.state

    def _get_details(self) -> GetFlowItemByIdEndpointOutput:
        """Fetch the full details of this flow item from the API."""
        return self._openapi_service.ranking_flow_item_api.flow_ranking_item_flow_item_id_get(
            flow_item_id=self.id,
        )

    def __str__(self) -> str:
        return f"FlowItem(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
