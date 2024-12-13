"""
Classify order with a validation set
"""

from rapidata import (
    RapidataClient,
    LabelingSelection,
    ConditionalValidationSelection,
)
from rapidata.rapidata_client.assets._media_asset import MediaAsset


def new_cond_validation_rapid_order(rapi: RapidataClient):
    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set = rapi.validation.create_classification_set(
        name="Example Classify Validation Set",
        instruction="What is shown in the image?",
        answer_options=["Fish", "Cat", "Wallaby", "Airplane"],
        truths=[["Wallaby"]],
        datapoints=["examples/data/wallaby.jpg"],
        prompts=["Hint: It has a pouch"],
    )
    # configure order
    selections = [
                ConditionalValidationSelection(
                    chances=[0.9],
                    thresholds=[0.35],
                    rapid_counts=[1],
                    validation_set_id=validation_set.id,
                ),
                LabelingSelection(amount=1),
            ]
    order = rapi.order.create_classification_order(
        name="Example Classify Order",
        instruction="What is shown in the image?",
        answer_options=["Fish", "Cat", "Wallaby", "Airplane"],
        datapoints=["examples/data/wallaby.jpg"],
        responses_per_datapoint=3,
        prompts=["Hint: It has a pouch"],
        selections=selections
    ).run()

    result = order.get_status()
    print("Order in state: ", result)

    return order


if __name__ == "__main__":
    order = new_cond_validation_rapid_order(RapidataClient())
