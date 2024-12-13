'''
Compare order with a validation set
'''

from rapidata import RapidataClient


def new_compare_order(rapi: RapidataClient):
    logo_path = "https://assets.rapidata.ai/rapidata_logo.png"
    concept_path = "https://assets.rapidata.ai/rapidata_concept_logo.jpg"
    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set = rapi.validation.create_compare_set(
        name="Example Compare Validation Set",
        instruction="Which logo is the actual Rapidata logo?",
        datapoints=[[logo_path, concept_path]],
        truths=[logo_path],
    )

    # configure order
    order = rapi.order.create_compare_order(
        name="Example Compare Order",
        instruction="Which logo is better?",
        datapoints=[[concept_path, logo_path]],
        responses_per_datapoint=10,
        validation_set_id=validation_set.id
    ).run()

    return order


if __name__ == "__main__":
    order = new_compare_order(RapidataClient())
    order.display_progress_bar()
    results = order.get_results()
    print(results)
