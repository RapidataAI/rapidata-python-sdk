from rapidata.api_client.models.private_text_metadata_input import (
    PrivateTextMetadataInput,
)
from rapidata.rapidata_client.metadata._base_metadata import Metadata


class PrivateTextMetadata(Metadata):

    def __init__(self, text: str, identifier: str = "private_text"):
        super().__init__()
        self.identifier = identifier
        self._text = text

    def to_model(self):
        return PrivateTextMetadataInput(
            _t="PrivateTextMetadataInput", identifier=self.identifier, text=self._text
        )
