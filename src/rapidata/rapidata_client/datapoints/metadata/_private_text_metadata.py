from rapidata.api_client.models.private_text_metadata_input import (
    PrivateTextMetadataInput,
)
from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from pydantic import BaseModel


class PrivateTextMetadata(Metadata, BaseModel):

    text: str
    identifier: str = "private_text"

    def to_model(self):
        return PrivateTextMetadataInput(
            _t="PrivateTextMetadataInput", identifier=self.identifier, text=self.text
        )
