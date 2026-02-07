from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.service.openapi_service import OpenAPIService

if TYPE_CHECKING:
    from rapidata.rapidata_client.flow.rapidata_flow_item import RapidataFlowItem
    from rapidata.api_client.models.flow_item_state import FlowItemState


class RapidataFlow:
    def __init__(self, id: str, name: str, openapi_service: OpenAPIService):
        self.id = id
        self.name = name
        self._openapi_service = openapi_service

    def create_new_flow_batch(
        self,
        datapoints: list[str],
        data_type: Literal["media", "text"] = "media",
        private_metadata: list[dict[str, str]] | None = None,
        accept_failed_uploads: bool = False,
    ) -> RapidataFlowItem:
        """Create a new flow batch by uploading datapoints to a dataset and submitting it.

        Args:
            datapoints: The list of datapoints (paths or URLs) to upload.
            data_type: The data type of the datapoints. Defaults to "media".
            private_metadata: Optional key-value metadata per datapoint.
            accept_failed_uploads: If True, continues even if some uploads fail.

        Returns:
            RapidataFlowItem: The created flow item.
        """
        with tracer.start_as_current_span("RapidataFlow.create_new_flow_batch"):
            from rapidata.api_client.models.create_dataset_endpoint_input import (
                CreateDatasetEndpointInput,
            )
            from rapidata.api_client.models.create_flow_item_endpoint_input import (
                CreateFlowItemEndpointInput,
            )
            from rapidata.rapidata_client.flow.rapidata_flow_item import (
                RapidataFlowItem,
            )

            logger.debug("Creating flow item for flow '%s'", self.name)

            datapoints_instances = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                data_type=data_type,
                private_metadata=private_metadata,
            )
            dataset = self._openapi_service.dataset_api.dataset_post(
                create_dataset_endpoint_input=CreateDatasetEndpointInput(
                    name=self.name + "_dataset",
                ),
            )
            rapidata_dataset = RapidataDataset(
                dataset.dataset_id, self._openapi_service
            )

            with tracer.start_as_current_span("add_datapoints"):
                _, failed_uploads = rapidata_dataset.add_datapoints(
                    datapoints_instances
                )

                if failed_uploads and not accept_failed_uploads:
                    raise FailedUploadException(rapidata_dataset, failed_uploads)
                elif failed_uploads:
                    logger.warning(
                        "Failed to upload %d datapoints", len(failed_uploads)
                    )

            response = self._openapi_service.ranking_flow_item_api.flow_ranking_flow_id_item_post(
                flow_id=self.id,
                create_flow_item_endpoint_input=CreateFlowItemEndpointInput(
                    datasetId=rapidata_dataset.id,
                ),
            )

            logger.debug("Flow item created with id: %s", response.flow_item_id)

            return RapidataFlowItem(
                id=response.flow_item_id,
                flow_id=self.id,
                openapi_service=self._openapi_service,
            )

    def get_flow_items(
        self, state: FlowItemState | None = None
    ) -> list[RapidataFlowItem]:
        """Query flow items for this flow.

        Args:
            state: Optional state filter (Pending, Running, Completed, Failed).

        Returns:
            list[RapidataFlowItem]: A list of flow items.
        """
        with tracer.start_as_current_span("RapidataFlow.get_flow_items"):
            from rapidata.rapidata_client.flow.rapidata_flow_item import (
                RapidataFlowItem,
            )

            logger.debug("Getting flow items for flow '%s', state=%s", self.name, state)

            response = self._openapi_service.ranking_flow_item_api.flow_ranking_flow_id_item_get(
                flow_id=self.id,
                state=state,
            )

            return [
                RapidataFlowItem(
                    id=item.id,
                    flow_id=self.id,
                    openapi_service=self._openapi_service,
                )
                for item in response.items
            ]

    def update_config(
        self,
        instruction: str | None = None,
        context: str | None = None,
        starting_elo: int | None = None,
        k_factor: int | None = None,
        scaling_factor: int | None = None,
        responses_per_comparison: int | None = None,
    ) -> None:
        """Update the configuration of this ranking flow.

        Args:
            instruction: New instruction for comparisons.
            context: New context shown alongside the instruction.
            starting_elo: New starting ELO rating.
            k_factor: New K-factor for ELO calculations.
            scaling_factor: New scaling factor for ELO calculations.
            responses_per_comparison: New number of responses per comparison.
        """
        with tracer.start_as_current_span("RapidataFlow.update_config"):
            from rapidata.api_client.models.update_config_endpoint_input import (
                UpdateConfigEndpointInput,
            )

            logger.debug("Updating config for flow '%s'", self.name)

            self._openapi_service.ranking_flow_api.flow_ranking_flow_id_config_patch(
                flow_id=self.id,
                update_config_endpoint_input=UpdateConfigEndpointInput(
                    criteria=instruction,
                    context=context,
                    startingElo=starting_elo,
                    kFactor=k_factor,
                    scalingFactor=scaling_factor,
                    responsesRequired=responses_per_comparison,
                ),
            )

    def delete(self) -> None:
        """Soft delete this flow."""
        with tracer.start_as_current_span("RapidataFlow.delete"):
            logger.debug("Deleting flow '%s'", self.name)
            self._openapi_service.flow_api.flow_flow_id_delete(flow_id=self.id)

    def __str__(self) -> str:
        return f"Flow(id={self.id}, name={self.name})"

    def __repr__(self) -> str:
        return self.__str__()
