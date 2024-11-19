'''
Transcription order with validation set
'''

from rapidata import (
    RapidataClient,
    Settings,
    NaiveReferee,
    TranscriptionWorkflow,
    TranscriptionMetadata,
    ValidationSelection,
    LabelingSelection,
    MediaAsset,
)


def new_transcription_order(rapi: RapidataClient):
    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set = (
        rapi.new_validation_set(
            name="Example Transcription Validation Set"
        ).add_transcription_rapid(
            asset=MediaAsset("examples/data/waiting.mp4"),
            question="Click any words that are part of a name",
            transcription="This is Mr. Bean waiting for his friends",
            truths=[2, 3],
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
        .referee(NaiveReferee(responses=30))
        .settings(Settings().alert_on_fast_response(4000))
        .media(asset=[MediaAsset("examples/data/waiting.mp4")], metadata=[transcription])
        .selections([
            ValidationSelection(amount=1, validation_set_id=validation_set.id),
            LabelingSelection(amount=2)
        ])
        .create()
    )

    return order

if __name__ == "__main__":
    new_transcription_order(RapidataClient())
