from rapidata.api_client.models.private_text_metadata_input import (
    PrivateTextMetadataInput,
)
from rapidata.rapidata_client.metadata.base_metadata import Metadata


class PrivateTextMetadata(Metadata):

    def __init__(self, text: str, identifier: str = "private_text"):
        super().__init__(identifier=identifier)
        self._text = text

    def to_model(self):
        return PrivateTextMetadataInput(
            _t="PrivateTextMetadataInput", identifier=self._identifier, text=self._text
        )
