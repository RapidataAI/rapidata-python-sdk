from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from rapidata.api_client.models.prompt_metadata_input import PromptMetadataInput
from pydantic import BaseModel


class PromptMetadata(Metadata, BaseModel):
    """The PromptMetadata class is used to display a prompt to the user."""

    prompt: str

    def to_model(self):
        return PromptMetadataInput(_t="PromptMetadataInput", prompt=self.prompt)
