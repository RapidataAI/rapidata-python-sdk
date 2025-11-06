from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.create_datapoint_model import CreateDatapointModel
from rapidata.api_client.models.create_datapoint_model_asset import (
    CreateDatapointModelAsset,
)
from rapidata.api_client.models.create_datapoint_model_context_asset import (
    CreateDatapointModelContextAsset,
)
from rapidata.api_client.models.create_datapoint_result import CreateDatapointResult
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader


class DatapointUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_datapoint(
        self, datapoint: Datapoint, dataset_id: str, index: int
    ) -> CreateDatapointResult:

        uploaded_asset = (
            self._handle_media_datapoint(datapoint)
            if datapoint.data_type == "media"
            else self._handle_text_datapoint(datapoint)
        )
        return self.openapi_service.dataset_api.dataset_dataset_id_datapoint_post(
            dataset_id=dataset_id,
            create_datapoint_model=CreateDatapointModel(
                asset=uploaded_asset,
                context=datapoint.context,
                contextAsset=(
                    CreateDatapointModelContextAsset(
                        actual_instance=self.asset_uploader.get_uploaded_asset_input(
                            datapoint.media_context
                        )
                    )
                    if datapoint.media_context
                    else None
                ),
                transcription=datapoint.sentence,
                sortIndex=index,
                group=datapoint.group,
            ),
        )

    def _handle_text_datapoint(self, datapoint: Datapoint) -> CreateDatapointModelAsset:
        return CreateDatapointModelAsset(
            actual_instance=self.asset_uploader.get_uploaded_text_input(
                datapoint.asset
            ),
        )

    def _handle_media_datapoint(
        self, datapoint: Datapoint
    ) -> CreateDatapointModelAsset:
        return CreateDatapointModelAsset(
            actual_instance=self.asset_uploader.get_uploaded_asset_input(
                datapoint.asset
            ),
        )
