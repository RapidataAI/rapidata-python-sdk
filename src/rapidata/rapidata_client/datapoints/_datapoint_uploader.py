from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._asset_mapper import AssetMapper

if TYPE_CHECKING:
    from rapidata.api_client.models.create_datapoint_result import CreateDatapointResult
    from rapidata.api_client.models.i_asset_input import IAssetInput


class DatapointUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)
        self.asset_mapper = AssetMapper()

    def _upload_and_map_asset(self, asset: str | list[str]) -> IAssetInput:
        """Upload asset(s) and map to IAssetInput."""

        if isinstance(asset, list):
            uploaded_names = [self.asset_uploader.upload_asset(a) for a in asset]
            return self.asset_mapper.create_existing_asset_input(uploaded_names)
        else:
            uploaded_name = self.asset_uploader.upload_asset(asset)
            return self.asset_mapper.create_existing_asset_input(uploaded_name)

    def upload_datapoint(
        self, datapoint: Datapoint, dataset_id: str, index: int
    ) -> CreateDatapointResult:
        from rapidata.api_client.models.create_datapoint_model import (
            CreateDatapointModel,
        )

        if datapoint.data_type == "media":
            uploaded_asset = self._upload_and_map_asset(datapoint.asset)
        else:
            uploaded_asset = self.asset_mapper.create_text_input(datapoint.asset)

        return self.openapi_service.dataset_api.dataset_dataset_id_datapoint_post(
            dataset_id=dataset_id,
            create_datapoint_model=CreateDatapointModel(
                asset=uploaded_asset,
                context=datapoint.context,
                contextAsset=(
                    self.asset_mapper.create_existing_asset_input(
                        self.asset_uploader.upload_asset(datapoint.media_context)
                    )
                    if datapoint.media_context
                    else None
                ),
                transcription=datapoint.sentence,
                sortIndex=index,
                group=datapoint.group,
                privateMetadata=datapoint.private_metadata,
            ),
        )
