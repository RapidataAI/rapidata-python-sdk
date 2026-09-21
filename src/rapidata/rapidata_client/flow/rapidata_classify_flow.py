from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from rapidata.rapidata_client.config import tracer
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.flow.rapidata_flow import RapidataFlow

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.flow.rapidata_flow_item import RapidataFlowItem


class RapidataClassifyFlow(RapidataFlow):
    def __init__(self, id: str, name: str, openapi_service: OpenAPIService):
        super().__init__(id, name, openapi_service, flow_type="simple")

    def create_new_flow_batch(
        self,
        datapoints: list[str],
        contexts: list[str] | None = None,
        context_assets: list[list[str]] | None = None,
        data_type: Literal["media", "text"] = "media",
        private_metadata: list[dict[str, str]] | None = None,
        accept_failed_uploads: bool = False,
        time_to_live: int | None = None,
    ) -> RapidataFlowItem:
        """Classify a batch with one context and one list of context assets per datapoint."""
        from rapidata.api_client.models.create_simple_flow_item_endpoint_input import (
            CreateSimpleFlowItemEndpointInput,
        )
        from rapidata.rapidata_client.flow.rapidata_flow_item import RapidataFlowItem

        with tracer.start_as_current_span("RapidataClassifyFlow.create_new_flow_batch"):
            self._validate_time_to_live(time_to_live)
            if contexts is not None:
                if not isinstance(contexts, list) or any(
                    not isinstance(value, str) for value in contexts
                ):
                    raise ValueError("Contexts must be a list of strings.")
                if len(contexts) != len(datapoints):
                    raise ValueError(
                        "Number of contexts must match number of datapoints."
                    )
            if context_assets is not None:
                if not isinstance(context_assets, list) or any(
                    not isinstance(assets, list)
                    or any(not isinstance(asset, str) for asset in assets)
                    for assets in context_assets
                ):
                    raise ValueError(
                        "Context assets must be a list of lists of strings."
                    )
                if len(context_assets) != len(datapoints):
                    raise ValueError(
                        "Number of context assets entries must match number of datapoints."
                    )
            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=context_assets,
                data_type=data_type,
                private_metadata=private_metadata,
            )
            dataset = self._upload_dataset(datapoints_instances, accept_failed_uploads)
            response = self._openapi_service.flow.simple_flow_item_api.flow_simple_flow_id_item_post(
                flow_id=self.id,
                create_simple_flow_item_endpoint_input=CreateSimpleFlowItemEndpointInput(
                    datasetId=dataset.id,
                    timeToLiveInSeconds=time_to_live,
                ),
            )
            return RapidataFlowItem(
                id=response.flow_item_id,
                flow_id=self.id,
                openapi_service=self._openapi_service,
                flow_type=self._flow_type,
            )
