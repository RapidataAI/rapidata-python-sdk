from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.api_client.models.prompt_metadata_input import PromptMetadataInput


class PromptMetadata(Metadata):

    def __init__(self, prompt: str, identifier: str = "prompt"):
        super().__init__(identifier=identifier)
        self._prompt = prompt
    

    def to_model(self):
        return PromptMetadataInput(_t="PromptMetadataInput", identifier=self._identifier, prompt=self._prompt)