from rapidata.api_client.models.private_text_metadata_input import (
    PrivateTextMetadataInput,
)
from rapidata.rapidata_client.metadata._base_metadata import Metadata


class PrivateTextMetadata(Metadata):

    def __init__(self, text: str, identifier: str = "private_text"):
        super().__init__(identifier=identifier)
        self._text = text

    def _to_model(self):
        return PrivateTextMetadataInput(
            _t="PrivateTextMetadataInput", identifier=self._identifier, text=self._text
        )
