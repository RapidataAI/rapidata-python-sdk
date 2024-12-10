"""
Classify order with a validation set
"""

from rapidata import RapidataClient


def new_classify_text_asset_order(rapi: RapidataClient):
    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set = rapi.validation.create_classification_set(
        name="Example Text Classification Validation Set",
        question="How does this song continue?",
        options=["Baby don't hurt me", "No more", "Illusions", "Submarine", "Rock you"],
        truths=[["Baby don't hurt me"]],
        datapoints=["What is love?"],
        data_type="text"
    )

    # Configure order
    order = rapi.order.create_classification_order(
        name="Example Text Classify Order",
        question="How does this song continue?",
        options=["Baby don't hurt me", "No more", "Illusions", "Submarine", "Rock you"],
        datapoints=["We will, we will ...", "We all live in a yellow ..."],
        data_type="text",
        responses_per_datapoint=3,
        validation_set_id=validation_set.id
    ).run()

    return order


if __name__ == "__main__":
    order = new_classify_text_asset_order(RapidataClient())
    order.display_progress_bar()
    results = order.get_results()
    print(results)
