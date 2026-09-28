from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint
    from rapidata.rapidata_client.flow._flow_type import FlowType
    from rapidata.rapidata_client.flow.rapidata_flow_item import RapidataFlowItem


class RapidataFlow:
    def __init__(
        self,
        id: str,
        name: str,
        openapi_service: OpenAPIService,
        flow_type: FlowType,
    ):
        self.id = id
        self.name = name
        self._openapi_service = openapi_service
        self._flow_type: FlowType = flow_type

    @staticmethod
    def _validate_time_to_live(time_to_live: int | None) -> None:
        # The backend reserves a 40s drain at the end of each batch and needs 30s of serving before it.
        if time_to_live is not None and not 70 <= time_to_live <= 3600:
            raise ValueError("Time to live must be between 70 seconds and 1 hour.")

    def _upload_dataset(
        self,
        datapoints: list[Datapoint],
        accept_failed_uploads: bool,
    ) -> RapidataDataset:
        from rapidata.api_client.models.create_dataset_endpoint_input import (
            CreateDatasetEndpointInput,
        )

        dataset = self._openapi_service.dataset.dataset_api.dataset_post(
            create_dataset_endpoint_input=CreateDatasetEndpointInput(
                name=self.name + "_dataset"
            ),
        )
        rapidata_dataset = RapidataDataset(dataset.dataset_id, self._openapi_service)
        with tracer.start_as_current_span("add_datapoints"):
            _, failed_uploads = rapidata_dataset.add_datapoints(datapoints)
            if failed_uploads and not accept_failed_uploads:
                raise FailedUploadException(rapidata_dataset, failed_uploads)
            if failed_uploads:
                logger.warning("Failed to upload %d datapoints", len(failed_uploads))
        return rapidata_dataset

    def get_flow_items(self, amount: int = 10, page: int = 1) -> list[RapidataFlowItem]:
        """Query flow items for this flow, newest first."""
        with tracer.start_as_current_span("RapidataFlow.get_flow_items"):
            from rapidata.rapidata_client.flow.rapidata_flow_item import (
                RapidataFlowItem,
            )

            logger.debug("Getting flow items for flow '%s'", self.name)

            response = self._openapi_service.flow.ranking_flow_item_api.flow_ranking_flow_id_item_get(
                flow_id=self.id,
                sort=["-created_at"],
                page=page,
                page_size=amount,
            )

            return [
                RapidataFlowItem(
                    id=item.id,
                    flow_id=self.id,
                    openapi_service=self._openapi_service,
                    flow_type=self._flow_type,
                )
                for item in response.items
            ]

    def delete(self) -> None:
        """Soft delete this flow."""
        with tracer.start_as_current_span("RapidataFlow.delete"):
            logger.debug("Deleting flow '%s'", self.name)
            self._openapi_service.flow.flow_api.flow_flow_id_delete(flow_id=self.id)

    def __str__(self) -> str:
        return f"Flow(id={self.id}, name={self.name})"

    def __repr__(self) -> str:
        return self.__str__()
