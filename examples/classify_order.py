'''
Classify order with a validation set
'''

from rapidata import RapidataClient


def new_classify_order(rapi: RapidataClient):
    # Validation set
    # This will be shown as defined in the ValidationSelection and will make our annotators understand the task better
    validation_set_builder = rapi.new_validation_set("Example Classification Validation Set")

    validation_set = validation_set_builder.add_rapid(
        rapi.rapid_builder
        .classify_rapid()
        .question("What kind of animal is this?")
        .options(["Fish", "Marsupial", "Bird", "Reptile"])
        .media("https://assets.rapidata.ai/wallaby.jpg")
        .truths(["Marsupial"])
        .prompt("Hint: It has a pouch")
        .build()
    ).create()

    # Configure order
    order = (
        rapi.create_classify_order(name="Example Classify Order")
        .question("What is shown in the image?")
        .options(["Fish", "Cat", "Wallaby", "Airplane"])
        .media(["https://assets.rapidata.ai/wallaby.jpg"])
        .responses(3)
        .validation_set(validation_set.id)
        .run()
    )

    return order


if __name__ == "__main__":
    order = new_classify_order(RapidataClient())
    order.display_progress_bar()
    results = order.get_results()
    print(results)

