from rapidata.api_client.models.prompt_asset_metadata_input import (
    PromptAssetMetadataInput,
)
from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from rapidata.api_client.models.multi_asset_input_assets_inner import (
    ExistingAssetInput,
    MultiAssetInputAssetsInner,
)


class MediaAssetMetadata(Metadata):

    def __init__(self, internal_file_name: str):
        super().__init__()
        self._internal_file_name = internal_file_name

    def to_model(self):
        return PromptAssetMetadataInput(
            _t="PromptAssetMetadataInput",
            asset=MultiAssetInputAssetsInner(
                actual_instance=ExistingAssetInput(
                    _t="ExistingAssetInput",
                    name=self._internal_file_name,
                ),
            ),
        )
