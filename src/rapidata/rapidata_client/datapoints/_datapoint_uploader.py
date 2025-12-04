from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader

if TYPE_CHECKING:
    from rapidata.api_client.models.create_datapoint_result import CreateDatapointResult


class DatapointUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_datapoint(
        self, datapoint: Datapoint, dataset_id: str, index: int
    ) -> CreateDatapointResult:
        from rapidata.api_client.models.create_datapoint_model import (
            CreateDatapointModel,
        )
        from rapidata.api_client.models.i_asset_input import IAssetInput

        uploaded_asset: IAssetInput = (
            self.asset_uploader.get_uploaded_asset_input(datapoint.asset)
            if datapoint.data_type == "media"
            else self.asset_uploader.get_uploaded_text_input(datapoint.asset)
        )
        return self.openapi_service.dataset_api.dataset_dataset_id_datapoint_post(
            dataset_id=dataset_id,
            create_datapoint_model=CreateDatapointModel(
                asset=uploaded_asset,
                context=datapoint.context,
                contextAsset=(
                    self.asset_uploader.get_uploaded_asset_input(
                        datapoint.media_context
                    )
                    if datapoint.media_context
                    else None
                ),
                transcription=datapoint.sentence,
                sortIndex=index,
                group=datapoint.group,
            ),
        )
