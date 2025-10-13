from rapidata.api_client.models.public_text_metadata_input import (
    PublicTextMetadataInput,
)
from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from pydantic import BaseModel


class PublicTextMetadata(Metadata, BaseModel):

    text: str
    identifier: str = "public_text"

    def to_model(self):
        return PublicTextMetadataInput(
            _t="PublicTextMetadataInput", identifier=self.identifier, text=self.text
        )
