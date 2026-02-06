from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer
from rapidata.service.openapi_service import OpenAPIService

if TYPE_CHECKING:
    from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow


class RapidataFlowManager:
    """Handles everything regarding flows from creation to retrieval.

    A manager for creating, retrieving, and searching for flows.
    Flows are used to add small flow items that can be solved fast without the order creation overhead.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service

    def create_ranking_flow(
        self,
        name: str,
        instruction: str,
        responses_per_comparison: int = 1,
        context: str | None = None,
        starting_elo: int | None = None,
        k_factor: int | None = None,
        scaling_factor: int | None = None,
    ) -> RapidataFlow:
        """Create a new ranking flow.

        Args:
            name: The name of the flow.
            instruction: The instruction for the ranking comparisons. Will be shown with each matchup.
            responses_per_comparison: The number of responses per comparison. Defaults to 1.
            context: Optional context shown alongside the instruction.
            starting_elo: Optional starting ELO rating for items.
            k_factor: Optional K-factor for ELO calculations.
            scaling_factor: Optional scaling factor for ELO calculations.

        Returns:
            RapidataFlow: The created flow instance.
        """
        with tracer.start_as_current_span("RapidataFlowManager.create_ranking_flow"):
            from rapidata.api_client.models.create_flow_endpoint_input import (
                CreateFlowEndpointInput,
            )
            from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow

            logger.debug("Creating ranking flow: %s", name)

            response = self._openapi_service.ranking_flow_api.flow_ranking_post(
                create_flow_endpoint_input=CreateFlowEndpointInput(
                    name=name,
                    criteria=instruction,
                    context=context,
                    startingElo=starting_elo,
                    kFactor=k_factor,
                    scalingFactor=scaling_factor,
                    responsesRequired=responses_per_comparison,
                ),
            )

            logger.debug("Flow created with id: %s", response.flow_id)

            return RapidataFlow(
                id=response.flow_id,
                name=name,
                openapi_service=self._openapi_service,
            )

    def get_flow_by_id(self, flow_id: str) -> RapidataFlow:
        """Get a flow by its ID.

        Args:
            flow_id: The ID of the flow.

        Returns:
            RapidataFlow: The flow instance.
        """
        with tracer.start_as_current_span("RapidataFlowManager.get_flow_by_id"):
            from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow

            logger.debug("Getting flow by id: %s", flow_id)

            response = self._openapi_service.flow_api.flow_flow_id_get(
                flow_id=flow_id,
            )

            return RapidataFlow(
                id=response.id,
                name=response.name,
                openapi_service=self._openapi_service,
            )

    def find_flows(self, amount: int = 10) -> list[RapidataFlow]:
        """Find your recent flows.

        Args:
            amount: The maximum number of flows to return. Defaults to 10.

        Returns:
            list[RapidataFlow]: A list of RapidataFlow instances.
        """
        with tracer.start_as_current_span("RapidataFlowManager.find_flows"):
            from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow

            logger.debug("Finding flows, amount: %s", amount)

            response = self._openapi_service.flow_api.flow_get()

            return [
                RapidataFlow(
                    id=flow.id,
                    name=flow.name,
                    openapi_service=self._openapi_service,
                )
                for flow in response.items[:amount]
            ]

    def __str__(self) -> str:
        return "RapidataFlowManager"

    def __repr__(self) -> str:
        return self.__str__()
