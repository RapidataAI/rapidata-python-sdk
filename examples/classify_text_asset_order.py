"""
Classify order with a validation set
"""

from rapidata import RapidataClient


def new_classify_text_asset_order(rapi: RapidataClient):
    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set_builder = rapi.new_validation_set("Example Text Classification Validation Set")

    validation_set = validation_set_builder.add_rapid(
        rapi.rapid_builder
        .classify_rapid()
        .question("How does this song continue?")
        .options(["Baby don't hurt me", "No more", "Illusions", "Submarine", "Rock you"])
        .media("What is love?")
        .truths(["Baby don't hurt me"])
        .build()
    ).create()

    # Configure order
    order = (
        rapi.create_classify_order(name="Example Text Classify Order")
        .question("How does this song continue?")
        .options(["Baby don't hurt me", "No more", "Illusions", "Submarine", "Rock you"])
        .text(["We will, we will ...", "We all live in a yellow ..."])
        .responses(3)
        .validation_set(validation_set.id)
        .run()
    )

    return order


if __name__ == "__main__":
    order = new_classify_text_asset_order(RapidataClient())
    order.display_progress_bar()
    results = order.get_results()
    print(results)
