from __future__ import annotations

import warnings
from datetime import timedelta
from typing import TYPE_CHECKING, Sequence

from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.flow._flow_type import flow_type_from_api
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

if TYPE_CHECKING:
    from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow


class RapidataFlowManager:
    """Handles everything regarding flows from creation to retrieval.

    A manager for creating, retrieving, and searching for flows.
    Flows are used to add small flow items that can be solved fast without the job creation overhead.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service

    def create_ranking_flow(
        self,
        name: str,
        instruction: str,
        max_response_threshold: int = 100,
        min_response_threshold: int | None = None,
        validation_set_id: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> RapidataFlow:
        """Create a new ranking flow.

        Args:
            name: The name of the flow.
            instruction: The instruction for the ranking comparisons. Will be shown with each matchup.
            max_response_threshold: The maximum number of responses that will be collected per flow item. Defaults to 100.
            min_response_threshold: The minimum number of responses required for the flow to be considered complete in case of a timeout. Defaults to max_response_threshold.
            validation_set_id: Optional validation set ID.
            settings: Optional settings for the flow.

        Returns:
            RapidataFlow: The created flow instance.
        """
        if min_response_threshold is None:
            min_response_threshold = max_response_threshold

        with tracer.start_as_current_span("RapidataFlowManager.create_ranking_flow"):
            from rapidata.api_client.models.create_flow_endpoint_input import (
                CreateFlowEndpointInput,
            )
            from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow

            logger.debug("Creating ranking flow: %s", name)

            response = self._openapi_service.flow.ranking_flow_api.flow_ranking_post(
                create_flow_endpoint_input=CreateFlowEndpointInput(
                    name=name,
                    criteria=instruction,
                    validationSetId=validation_set_id,
                    minResponses=min_response_threshold,
                    maxResponses=max_response_threshold,
                    featureFlags=(
                        [setting._to_feature_flag() for setting in settings]
                        if settings
                        else None
                    ),
                ),
            )

            logger.debug("Flow created with id: %s", response.flow_id)

            return RapidataFlow(
                id=response.flow_id,
                name=name,
                openapi_service=self._openapi_service,
            )

    def create_classify_flow(
        self,
        name: str,
        instruction: str,
        categories: list[str] | list[tuple[str, str]],
        max_responses_per_datapoint: int = 15,
        min_responses_per_datapoint: int = 10,
        time_to_live: timedelta | int | None = None,
        validation_set_id: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
        *,
        responses_per_datapoint: int | None = None,
    ) -> RapidataFlow:
        """Create a new classify flow.

        Every flow item sorts each of its datapoints into one of the flow's categories.

        Args:
            name: The name of the flow.
            instruction: The question shown with every datapoint, e.g. "Does this image contain text?".
            categories: Between 2 and 10 answer options. A string is shown to annotators and returned in the results as is; a `(label, value)` tuple shows the label and returns the value.
            max_responses_per_datapoint: The number of accepted responses that closes an image. Defaults to 15, must be at least min_responses_per_datapoint.
            min_responses_per_datapoint: The average responses per image an item needs, once it ends by time_to_live, to be Completed rather than Incomplete. Defaults to 10, at least 1.
            time_to_live: The flow's default time to live, as a timedelta or in seconds, between 45 seconds and 1 hour. Defaults to 4 minutes when omitted. Each batch can override this with its own `time_to_live`.
            validation_set_id: Optional validation set ID.
            settings: Optional settings for the flow.
            responses_per_datapoint: Deprecated, use max_responses_per_datapoint. Sets both max and min to this value.

        Returns:
            RapidataFlow: The created flow instance.
        """
        if responses_per_datapoint is not None:
            warnings.warn(
                "responses_per_datapoint is deprecated, use max_responses_per_datapoint"
                " (and optionally min_responses_per_datapoint).",
                DeprecationWarning,
                stacklevel=2,
            )
            max_responses_per_datapoint = responses_per_datapoint
            min_responses_per_datapoint = responses_per_datapoint

        category_pairs: list[tuple[str, str]] = [
            (
                (category, category)
                if isinstance(category, str)
                else (category[0], category[1])
            )
            for category in categories
        ]
        if not 2 <= len(category_pairs) <= 10:
            raise ValueError("Categories must contain between 2 and 10 entries.")
        values = [value for _, value in category_pairs]
        if len(set(values)) != len(values):
            raise ValueError("Category values must be unique.")
        if min_responses_per_datapoint < 1:
            raise ValueError("Min responses per datapoint must be at least 1.")
        if max_responses_per_datapoint < min_responses_per_datapoint:
            raise ValueError(
                "Max responses per datapoint must be at least min responses per datapoint."
            )
        if isinstance(time_to_live, timedelta):
            time_to_live_seconds = int(time_to_live.total_seconds())
        else:
            time_to_live_seconds = time_to_live
        if time_to_live_seconds is not None and not 45 <= time_to_live_seconds <= 3600:
            raise ValueError("Time to live must be between 45 seconds and 1 hour.")

        with tracer.start_as_current_span("RapidataFlowManager.create_classify_flow"):
            from rapidata.api_client.models.classify_blueprint_category import (
                ClassifyBlueprintCategory,
            )
            from rapidata.api_client.models.create_simple_flow_endpoint_input import (
                CreateSimpleFlowEndpointInput,
            )
            from rapidata.api_client.models.i_flow_rapid_blueprint_classify_blueprint import (
                IFlowRapidBlueprintClassifyBlueprint,
            )
            from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow

            logger.debug("Creating classify flow: %s", name)

            response = self._openapi_service.flow.simple_flow_api.flow_simple_post(
                create_simple_flow_endpoint_input=CreateSimpleFlowEndpointInput(
                    name=name,
                    blueprint=IFlowRapidBlueprintClassifyBlueprint(
                        _t="ClassifyBlueprint",
                        title=instruction,
                        categories=[
                            ClassifyBlueprintCategory(label=label, value=value)
                            for label, value in category_pairs
                        ],
                    ),
                    maxResponses=max_responses_per_datapoint,
                    minResponses=min_responses_per_datapoint,
                    defaultTimeToLiveSeconds=time_to_live_seconds,
                    validationSetId=validation_set_id,
                    featureFlags=(
                        [setting._to_feature_flag() for setting in settings]
                        if settings
                        else None
                    ),
                ),
            )

            logger.debug("Flow created with id: %s", response.flow_id)

            return RapidataFlow(
                id=response.flow_id,
                name=name,
                openapi_service=self._openapi_service,
                flow_type="simple",
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

            response = self._openapi_service.flow.flow_api.flow_flow_id_get(
                flow_id=flow_id,
            )

            flow = response.to_dict()
            if not isinstance(flow, dict):
                raise ValueError(f"Flow '{flow_id}' returned no flow details.")

            return RapidataFlow(
                id=flow["id"],
                name=flow["name"],
                openapi_service=self._openapi_service,
                flow_type=flow_type_from_api(flow["_t"]),
            )

    def find_flows(
        self, name: str = "", amount: int = 10, page: int = 1
    ) -> list[RapidataFlow]:
        """Find your recent flows.

        Args:
            name: The name of the flow - matching flow will contain the name. Defaults to "" for any flow.
            amount: The maximum number of flows to return. Defaults to 10.
            page: The page of flows to return. Defaults to 1.

        Returns:
            list[RapidataFlow]: A list of RapidataFlow instances.
        """
        with tracer.start_as_current_span("RapidataFlowManager.find_flows"):
            from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
                AudienceAudienceIdJobsGetJobIdParameter,
            )
            from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow

            logger.debug("Finding flows, amount: %s", amount)

            response = self._openapi_service.flow.flow_api.flow_get(
                page=page,
                page_size=amount,
                sort=["-created_at"],
                name=AudienceAudienceIdJobsGetJobIdParameter(contains=name),
            )

            return [
                RapidataFlow(
                    id=flow.id,
                    name=flow.name,
                    openapi_service=self._openapi_service,
                    flow_type=flow_type_from_api(flow.type.value),
                )
                for flow in response.items
            ]

    def preheat(self) -> None:
        """Preheat the boost system to reduce latency for upcoming flow items."""
        with tracer.start_as_current_span("RapidataFlowManager.preheat"):
            logger.debug("Preheating boost")
            self._openapi_service.campaign.campaign_api.campaign_boost_preheat_post()

    def __str__(self) -> str:
        return "RapidataFlowManager"

    def __repr__(self) -> str:
        return self.__str__()
