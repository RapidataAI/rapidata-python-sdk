'''
Compare order with a validation set
'''

from rapidata import RapidataClient

def new_compare_order(rapi: RapidataClient):
    logo_path = "https://assets.rapidata.ai/rapidata_logo.png"
    concept_path = "https://assets.rapidata.ai/rapidata_concept_logo.jpg"

    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set_builder = rapi.new_validation_set(name="Example SimpleMatchup Validation Set")

    validation_set = validation_set_builder.add_rapid(
        rapi.rapid_builder.compare_rapid()
        .criteria("Which logo is the actual Rapidata logo?")
        .media([logo_path, concept_path])
        .truth(logo_path)
        .build()
    ).submit()

    # configure order
    order = (
        rapi.order_builder
        .compare_order(name="Example SimpleMatchup Order")
        .criteria("Which logo is better?")
        .media([[concept_path, logo_path]])
        .responses(10)
        .prompts(["Hint: This is not a trick question"])
        .validation_set(validation_set.id)
        .submit()
    )

    return order


if __name__ == "__main__":
    new_compare_order(RapidataClient())
