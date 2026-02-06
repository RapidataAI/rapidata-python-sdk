from typing import Literal
from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.flow.rapidata_flow_item import RapidataFlowItem
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)


class RapidataFlow:
    def __init__(self, id: str, name: str, openapi_service: OpenAPIService):
        self.id = id
        self.name = name
        self._openapi_service = openapi_service

    def create_new_flow_batch(
        self,
        assets: list[str],
        contexts: list[str] | None = None,
        data_type: Literal["media", "text"] = "media",
        private_metadata: list[dict[str, str]] | None = None,
        accept_failed_uploads: bool = False,
    ) -> RapidataFlowItem:
        with tracer.start_as_current_span("create_new_flow_batch"):
            from rapidata.api_client.models.create_dataset_endpoint_input import (
                CreateDatasetEndpointInput,
            )

            datapoints = DatapointsValidator.map_datapoints(
                datapoints=assets,
                contexts=contexts,
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
                _, failed_uploads = rapidata_dataset.add_datapoints(datapoints)

                if failed_uploads and not accept_failed_uploads:
                    raise FailedUploadException(rapidata_dataset, failed_uploads)
                else:
                    logger.warning(f"Failed to upload {len(failed_uploads)} datapoints")

            # flow_item = self._openapi_service.flow_api.flow_flow_id_flow_batch_post(
            #     flow_id=self.id,
            #     create_flow_batch_model=CreateFlowBatchModel(
            #         dataset_id=rapidata_dataset.id,
            #     ),
            # )
            # return RapidataFlowItem(flow_item.id, flow_item.name, self._openapi_service)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name
