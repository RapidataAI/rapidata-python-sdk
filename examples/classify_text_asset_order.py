"""
Classify order with a validation set
"""

from examples.setup_client import setup_client
from rapidata import (
    RapidataClient,
    ClassifyWorkflow,
    NaiveReferee,
    LabelingSelection,
)


def new_classify_text_asset_order(rapi: RapidataClient):
    # Configure order
    order = (
        rapi.new_order(
            name="Example Classify Order",
        )
        .workflow(
            ClassifyWorkflow(
                question="How does this song continue?",
                options=["Baby don't hurt me", "No more", "Illusions"],
            )
        )
        .texts(
            texts=[
                "What is love?",
            ]
        )
        .referee(NaiveReferee(required_guesses=3))
        .selections(
            [
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
    order = new_classify_text_asset_order(rapi)
