from itertools import zip_longest
import os
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.multi_asset_input_assets_inner import (
    MultiAssetInputAssetsInner,
)
from rapidata.api_client.models.create_datapoint_model import CreateDatapointModel
from rapidata.api_client.models.create_datapoint_model_asset import (
    CreateDatapointModelAsset,
)
from rapidata.api_client.models.create_datapoint_from_files_model_metadata_inner import (
    CreateDatapointFromFilesModelMetadataInner,
)
from rapidata.rapidata_client.datapoints.asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints.metadata import (
    PromptMetadata,
    MediaAssetMetadata,
    PrivateTextMetadata,
    SelectWordsMetadata,
    Metadata,
)
import re


class DatapointUploader:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self.asset_uploader = AssetUploader(openapi_service)

    def upload_datapoint(
        self, datapoint: Datapoint, index: int
    ) -> CreateDatapointModel:
        metadata = self._get_metadata(datapoint)

        uploaded_asset = (
            self._handle_media_datapoint(datapoint)
            if datapoint.data_type == "media"
            else self._handle_text_datapoint(datapoint)
        )
        return CreateDatapointModel(
            asset=uploaded_asset,
            metadata=metadata,
            sortIndex=index,
        )

    def _get_metadata(
        self, datapoint: Datapoint
    ) -> list[CreateDatapointFromFilesModelMetadataInner]:
        datapoint_metadata: list[Metadata] = []
        if datapoint.context:
            datapoint_metadata.append(PromptMetadata(prompt=datapoint.context))
        if datapoint.sentence:
            datapoint_metadata.append(
                SelectWordsMetadata(select_words=datapoint.sentence)
            )
        if datapoint.media_context:
            datapoint_metadata.append(
                MediaAssetMetadata(
                    internal_file_name=self.asset_uploader.upload_asset(
                        datapoint.media_context
                    )
                )
            )
        if datapoint.private_note:
            datapoint_metadata.append(PrivateTextMetadata(text=datapoint.private_note))

        metadata = [
            CreateDatapointFromFilesModelMetadataInner(metadata.to_model())
            for metadata in datapoint_metadata
        ]

        return metadata

    def _handle_text_datapoint(self, datapoint: Datapoint) -> CreateDatapointModelAsset:
        if isinstance(datapoint.assets, list):
            asset = CreateDatapointModelAsset(
                _t="MultiAssetInput",
                assets=[
                    MultiAssetInputAssetsInner(_t="TextAssetInput", text=asset)
                    for asset in datapoint.assets
                ],
            )
        else:
            asset = CreateDatapointModelAsset(
                _t="TextAssetInput", text=datapoint.assets
            )
        return asset

    def _handle_media_datapoint(
        self, datapoint: Datapoint
    ) -> CreateDatapointModelAsset:
        if isinstance(datapoint.assets, list):
            asset = CreateDatapointModelAsset(
                _t="MultiAssetInput",
                assets=[
                    MultiAssetInputAssetsInner(
                        _t="ExistingAssetInput",
                        name=self.asset_uploader.upload_asset(asset),
                    )
                    for asset in datapoint.assets
                ],
            )
        else:
            asset = CreateDatapointModelAsset(
                _t="ExistingAssetInput",
                name=self.asset_uploader.upload_asset(datapoint.assets),
            )
        return asset
