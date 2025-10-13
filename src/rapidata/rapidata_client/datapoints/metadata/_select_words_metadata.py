from rapidata.api_client.models.transcription_metadata_input import (
    TranscriptionMetadataInput,
)
from rapidata.rapidata_client.datapoints.metadata._base_metadata import Metadata
from pydantic import BaseModel


class SelectWordsMetadata(Metadata, BaseModel):
    """SelectWordsMetadata Class is used to define the Sentence that will be display to the user."""

    select_words: str

    def to_model(self):
        return TranscriptionMetadataInput(
            _t="TranscriptionMetadataInput",
            transcription=self.select_words,
        )
