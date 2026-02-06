from __future__ import annotations

from typing import TYPE_CHECKING, Any
from time import sleep
from rapidata.rapidata_client.config import logger, tracer
from rapidata.service.openapi_service import OpenAPIService


if TYPE_CHECKING:
    from rapidata.api_client.models.get_ranking_flow_item_results_endpoint_output import (
        GetRankingFlowItemResultsEndpointOutput,
    )
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

    def get_results(self) -> list[dict[str, Any]]:
        """Get the results of this flow item from the API."""
        with tracer.start_as_current_span("RapidataFlowItem.get_results"):
            logger.debug("Getting results for flow item '%s'", self.id)
            self._wait_for_state(
                target_states=[FlowItemState.COMPLETED],
                check_interval=1,
                status_message="Flow item '%s' is in state %s, waiting for completion...",
            )

            results = self._openapi_service.ranking_flow_item_api.flow_ranking_item_flow_item_id_results_get(
                flow_item_id=self.id,
            )
            return [result.to_dict() for result in results.datapoints]

    def _wait_for_state(
        self,
        target_states: list[FlowItemState],
        check_interval: float = 1,
        status_message: str | None = None,
    ) -> str:
        """
        Wait until the order reaches one of the target states.

        Args:
            target_states: List of states to wait for
            check_interval: How often to check the state in seconds
            status_message: Optional message to display while waiting

        Returns:
            The final state reached
        """
        while (current_state := self.get_status()) not in target_states:
            if status_message:
                logger.debug(status_message, self, current_state)
            sleep(check_interval)

        return current_state

    def _get_details(self) -> GetFlowItemByIdEndpointOutput:
        """Fetch the full details of this flow item from the API."""
        return self._openapi_service.ranking_flow_item_api.flow_ranking_item_flow_item_id_get(
            flow_item_id=self.id,
        )

    def __str__(self) -> str:
        return f"FlowItem(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
