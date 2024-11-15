'''
Compare order with a validation set
'''
from rapidata import (RapidataClient, 
                      Settings, 
                      NaiveReferee, 
                      CompareWorkflow, 
                      ValidationSelection, 
                      LabelingSelection, 
                      MultiAsset, 
                      MediaAsset,
                      PromptMetadata)

def new_compare_order(rapi: RapidataClient):
    logo_path = "examples/data/rapidata_logo.png"
    concept_path = "examples/data/rapidata_concept_logo.jpg"

    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set = rapi.new_validation_set(
        name="Example SimpleMatchup Validation Set"
    ).add_compare_rapid(
        asset=MultiAsset([MediaAsset(logo_path), MediaAsset(concept_path)]),
        question="Which logo is the actual Rapidata logo?",
        truth=logo_path,
    ).create()

    # configure order
    order = (
        rapi.new_order(
            name="Example SimpleMatchup Order",
        )
        .workflow(
            CompareWorkflow(
                criteria="Which logo is better?",
            )
        )
        .referee(NaiveReferee(responses=1))
        .media(
            asset=[
                MultiAsset(
                    [MediaAsset(path="examples/data/rapidata_concept_logo.jpg"),
                    MediaAsset(path="examples/data/rapidata_logo.png")
                    ]
                )
            ],
            metadata=[
                PromptMetadata(prompt="Hint: This is not a trick question")
            ] # the Prompt will be shown to the annotators, this can be different for each datapoint
        )
        .selections(
            [
                ValidationSelection(amount=1, validation_set_id=validation_set.id),
                LabelingSelection(amount=1),
            ]
        )
        .create()
    )

    return order


if __name__ == "__main__":
    new_compare_order(RapidataClient())
