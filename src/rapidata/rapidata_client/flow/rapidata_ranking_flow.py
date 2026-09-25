from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.flow.rapidata_flow_item import RapidataFlowItem


class RapidataRankingFlow(RapidataFlow):
    def __init__(self, id: str, name: str, openapi_service: OpenAPIService):
        super().__init__(id, name, openapi_service, flow_type="ranking")

    def create_new_flow_batch(
        self,
        datapoints: list[str],
        context: str | None = None,
        context_assets: list[str] | None = None,
        data_type: Literal["media", "text"] = "media",
        private_metadata: list[dict[str, str]] | None = None,
        accept_failed_uploads: bool = False,
        time_to_live: int | None = None,
    ) -> RapidataFlowItem:
        """Rank a batch with shared text and asset context."""
        from rapidata.api_client.models.create_flow_item_endpoint_input import (
            CreateFlowItemEndpointInput,
        )
        from rapidata.rapidata_client.flow.rapidata_flow_item import RapidataFlowItem

        with tracer.start_as_current_span("RapidataRankingFlow.create_new_flow_batch"):
            self._validate_time_to_live(time_to_live)
            if context_assets is not None and not 1 <= len(context_assets) <= 10:
                raise ValueError("Context assets must contain between 1 and 10 assets.")
            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                data_type=data_type,
                private_metadata=private_metadata,
            )
            dataset = self._upload_dataset(datapoints_instances, accept_failed_uploads)
            context_asset_input = (
                AssetUploader(self._openapi_service).upload_and_map_asset(
                    context_assets
                )
                if context_assets
                else None
            )
            response = self._openapi_service.flow.ranking_flow_item_api.flow_ranking_flow_id_item_post(
                flow_id=self.id,
                create_flow_item_endpoint_input=CreateFlowItemEndpointInput(
                    datasetId=dataset.id,
                    context=context,
                    contextAsset=context_asset_input,
                    timeToLiveInSeconds=time_to_live,
                ),
            )
            return RapidataFlowItem(
                id=response.flow_item_id,
                flow_id=self.id,
                openapi_service=self._openapi_service,
                flow_type=self._flow_type,
            )

    def update_config(
        self,
        instruction: str | None = None,
        starting_elo: int | None = None,
        min_responses: int | None = None,
        max_responses: int | None = None,
        drain_duration: int | None = None,
    ) -> None:
        """Update the instruction and response thresholds of this ranking flow."""
        with tracer.start_as_current_span("RapidataFlow.update_config"):
            from rapidata.api_client.models.update_config_endpoint_input import (
                UpdateConfigEndpointInput,
            )

            logger.debug("Updating config for flow '%s'", self.name)

            update_input = UpdateConfigEndpointInput(
                criteria=instruction,
                startingElo=starting_elo,
                minResponses=min_responses,
                maxResponses=max_responses,
            )
            # The field is nullable, so passing None would reset the drain to follow the serve timeout.
            if drain_duration is not None:
                update_input.drain_duration_seconds = drain_duration

            self._openapi_service.flow.ranking_flow_api.flow_ranking_flow_id_patch(
                flow_id=self.id,
                update_config_endpoint_input=update_input,
            )
