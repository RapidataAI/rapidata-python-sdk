"""
Classify order with a validation set
"""

from examples.setup_client import setup_client
from rapidata import (
    RapidataClient,
    ClassifyWorkflow,
    NaiveReferee,
    LabelingSelection,
    ValidationSelection,
    TextAsset,
)


def new_classify_text_asset_order(rapi: RapidataClient):
    validation_set = (
        rapi.new_validation_set(
            name="Example Validation Set",
        )
        .add_classify_rapid(
            asset=TextAsset("What is love?"),
            question="How does this song continue? (val)",
            categories=["Baby don't hurt me", "No more", "Illusions"],
            truths=["Baby don't hurt me"],
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
                question="How does this song continue?",
                options=["Baby don't hurt me", "No more", "Illusions", "Submarine"],
            )
        )
        .media([TextAsset("What is love?"), TextAsset("We all live in a yellow ...")])
        .referee(NaiveReferee(responses=3))
        .selections(
            [
                ValidationSelection(amount=1, validation_set_id=validation_set.id),
                LabelingSelection(amount=1),
            ]
        )
        .create()
    )

    result = order.get_status()
    print("Order in state: ", result)

    return order


if __name__ == "__main__":
    rapi = setup_client()
    order = new_classify_text_asset_order(rapi)
