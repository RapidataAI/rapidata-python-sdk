from examples.setup_client import setup_client
from rapidata.api_client.models.transcription_word import TranscriptionWord
from rapidata.rapidata_client.feature_flags.feature_flags import FeatureFlags
from rapidata.rapidata_client.metadata.transcription_metadata import (
    TranscriptionMetadata,
)
from rapidata.rapidata_client.rapidata_client import RapidataClient
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.workflow.transcription_workflow import (
    TranscriptionWorkflow,
)


def new_transcription_order(rapi: RapidataClient):
    validation_set_id = (
        rapi.new_validation_set(
            name="Example Transcription Validation Set"
        ).add_transcription_rapid(
            media_path="examples/data/waiting.mp4",
            question="Click on 'Mr. Bean'",
            transcription=["This", "is", "Mr.", "Bean"],
            correct_words=["Mr.", "Bean"],
        )
    ).create()

    # Configure order
    transcription = TranscriptionMetadata(transcription="Where is everybody?")

    order = (
        rapi.new_order(
            name="Example Transcription Order",
        )
        .workflow(
            TranscriptionWorkflow(
                instruction="Listen to the audio. Select only the words that you hear. Tap icon to replay"
            )
        )
        .referee(NaiveReferee(required_guesses=30))
        .feature_flags(FeatureFlags().alert_on_fast_response(4))
        .media(media_paths=["examples/data/waiting.mp4"], metadata=[transcription])
        .validation_set(validation_set_id)
        .create()
    )


if __name__ == "__main__":
    rapi = setup_client()
    new_transcription_order(rapi)
