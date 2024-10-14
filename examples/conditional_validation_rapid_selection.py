"""
Classify order with a validation set
"""

from examples.setup_client import setup_client
from rapidata import (
    RapidataClient,
    ClassifyWorkflow,
    NaiveReferee,
    PromptMetadata,
    LabelingSelection,
    ConditionalValidationSelection,
)
from rapidata.rapidata_client.assets.media_asset import MediaAsset


def new_cond_validation_rapid_order(rapi: RapidataClient):
    # Validation set
    validation_set = (
        rapi.new_validation_set("Example Validation Set")
        .add_classify_rapid(
            asset=MediaAsset(path="examples/data/wallaby.jpg"),
            question="What kind of animal is this?",
            categories=["Fish", "Marsupial", "Bird", "Reptile"],
            truths=["Marsupial"],
            metadata=[PromptMetadata(prompt="Hint: It has a pouch")],
        )
        .create()
    )

    # Configure order
    order = (
        rapi.new_order(
            name="Example Classify Order",
        )
        .workflow(
            ClassifyWorkflow(
                question="What is shown in the image?",
                options=["Fish", "Cat", "Wallaby", "Airplane"],
            )
        )
        .media(["examples/data/wallaby.jpg"])
        .referee(NaiveReferee(required_guesses=3))
        .selections(
            [
                ConditionalValidationSelection(
                    chances=[0.9],
                    thresholds=[0.35],
                    rapid_counts=[1],
                    validation_set_id=validation_set.id,
                ),
                LabelingSelection(amount=1),
            ]
        )
        .create()
    )

    result = order.get_status()
    print("Order in state: ", result.state)

    return order


if __name__ == "__main__":
    rapi = setup_client()
    order = new_cond_validation_rapid_order(rapi)
