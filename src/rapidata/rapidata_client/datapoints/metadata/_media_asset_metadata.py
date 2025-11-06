from rapidata.api_client.models.prompt_asset_metadata_input import (
    PromptAssetMetadataInput,
)
from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from rapidata.api_client.models.multi_asset_input_assets_inner import (
    ExistingAssetInput,
)
from rapidata.api_client.models.prompt_asset_metadata_input_asset import (
    PromptAssetMetadataInputAsset,
)
from pydantic import BaseModel


class MediaAssetMetadata(Metadata, BaseModel):
    internal_file_name: str

    def to_model(self):
        return PromptAssetMetadataInput(
            _t="PromptAssetMetadataInput",
            asset=PromptAssetMetadataInputAsset(
                actual_instance=ExistingAssetInput(
                    _t="ExistingAssetInput",
                    name=self.internal_file_name,
                ),
            ),
        )
