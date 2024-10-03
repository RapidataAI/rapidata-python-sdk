'''
Transcription order with validation set
'''
from examples.setup_client import setup_client
from rapidata import RapidataClient, FeatureFlags, NaiveReferee, TranscriptionWorkflow, TranscriptionMetadata, ValidationSelection, LabelingSelection


def new_transcription_order(rapi: RapidataClient):
    validation_set = (
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
        .feature_flags(FeatureFlags().alert_on_fast_response(4000))
        .media(media_paths=["examples/data/waiting.mp4"], metadata=[transcription])
        .selections([
            ValidationSelection(amount=1, validation_set_id=validation_set.id),
            LabelingSelection(amount=2)
        ])
        .create()
    )

    return order

if __name__ == "__main__":
    rapi = setup_client()
    new_transcription_order(rapi)
