from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from rapidata.api_client.models.private_text_metadata_input import (
    PrivateTextMetadataInput,
)
from pydantic import BaseModel


class PromptIdentifierMetadata(Metadata, BaseModel):
    identifier: str

    def to_model(self):
        return PrivateTextMetadataInput(
            _t="PrivateTextMetadataInput", identifier="prompt-id", text=self.identifier
        )
