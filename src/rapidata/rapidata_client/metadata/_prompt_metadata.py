from rapidata.rapidata_client.metadata._base_metadata import Metadata
from rapidata.api_client.models.prompt_metadata_input import PromptMetadataInput


class PromptMetadata(Metadata):
    """The PromptMetadata class is used to display a prompt to the user."""

    def __init__(self, prompt: str, identifier: str = "prompt"):
        super().__init__(identifier=identifier)

        if not isinstance(prompt, str):
            raise ValueError("Prompt must be a string")
        
        self._prompt = prompt
    

    def _to_model(self):
        return PromptMetadataInput(_t="PromptMetadataInput", identifier=self._identifier, prompt=self._prompt)
