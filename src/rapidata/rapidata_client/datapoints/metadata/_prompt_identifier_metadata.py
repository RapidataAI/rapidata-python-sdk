from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from rapidata.api_client.models.private_text_metadata_input import (
    PrivateTextMetadataInput,
)


class PromptIdentifierMetadata(Metadata):
    def __init__(self, identifier: str):
        super().__init__()
        self._identifier = identifier

    def to_model(self):
        return PrivateTextMetadataInput(
            _t="PrivateTextMetadataInput", identifier="prompt-id", text=self._identifier
        )
