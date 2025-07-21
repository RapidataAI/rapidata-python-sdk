from rapidata.api_client.models.prompt_asset_metadata_input import PromptAssetMetadataInput
from rapidata.api_client.models.url_asset_input import UrlAssetInput
from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from rapidata.api_client.models.prompt_asset_metadata_input_asset import PromptAssetMetadataInputAsset


class MediaAssetMetadata(Metadata):

    def __init__(self, url: str):
        super().__init__()
        self._url = url

    def to_model(self):
        return PromptAssetMetadataInput(
            _t="PromptAssetMetadataInput", 
            asset=PromptAssetMetadataInputAsset(
                actual_instance=UrlAssetInput(
                    _t="UrlAssetInput", 
                    url=self._url
                )
            )
        )
