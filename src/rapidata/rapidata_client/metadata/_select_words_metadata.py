from rapidata.api_client.models.transcription_metadata_input import (
    TranscriptionMetadataInput,
)
from rapidata.rapidata_client.metadata._base_metadata import Metadata


class SelectWordsMetadata(Metadata):
    """SelectWordsMetadata Class is used to define the Sentence that will be display to the user."""

    def __init__(self, select_words: str, identifier: str = "transcription"):
        super().__init__(identifier=identifier)
        self.identifier = identifier
        self.select_words = select_words

    def _to_model(self):
        return TranscriptionMetadataInput(
            _t="TranscriptionMetadataInput",
            identifier=self.identifier,
            transcription=self.select_words,
        )
