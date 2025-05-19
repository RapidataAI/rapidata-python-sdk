from rapidata.api_client.models.prompt_asset_metadata_input import PromptAssetMetadataInput
from rapidata.api_client.models.url_asset_input import UrlAssetInput
from rapidata.rapidata_client.metadata._base_metadata import Metadata


class MediaAssetMetadata(Metadata):

    def __init__(self, url: str):
        super().__init__()
        self._url = url

    def to_model(self):
        return PromptAssetMetadataInput(
            _t="PromptAssetMetadataInput", asset=UrlAssetInput(_t="UrlAssetInput", url=self._url)
        )
