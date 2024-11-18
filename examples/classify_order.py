'''
Classify order with a validation set
'''

from rapidata import (
    RapidataClient,
    ClassifyWorkflow,
    NaiveReferee,
    PromptMetadata,
    LabelingSelection,
    ValidationSelection,
    MediaAsset,
)


def new_classify_order(rapi: RapidataClient):
    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set = (
        rapi.new_validation_set("Example Validation Set")
        .add_classify_rapid(
            asset=MediaAsset(path="examples/data/wallaby.jpg"),
            question="What kind of animal is this?",
            categories=["Fish", "Marsupial", "Bird", "Reptile"],
            truths=["Marsupial"], # multiple correct answers are supported
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
        .media([MediaAsset("examples/data/wallaby.jpg")])
        .referee(NaiveReferee(responses=3))
        .selections([
            ValidationSelection(amount=1, validation_set_id=validation_set.id),
            LabelingSelection(amount=3)
            ])
        .create()
    )

    result = order.get_status()
    print("Order in state: ", result)

    return order


if __name__ == "__main__":
    order = new_classify_order(RapidataClient())
