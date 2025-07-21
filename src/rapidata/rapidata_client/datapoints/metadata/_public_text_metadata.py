from rapidata.api_client.models.public_text_metadata_input import (
    PublicTextMetadataInput,
)
from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata


class PublicTextMetadata(Metadata):

    def __init__(self, text: str, identifier: str = "public_text"):
        super().__init__()
        self._identifier = identifier
        self._text = text

    def to_model(self):
        return PublicTextMetadataInput(
            _t="PublicTextMetadataInput", identifier=self._identifier, text=self._text
        )
