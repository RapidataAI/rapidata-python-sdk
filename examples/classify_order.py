'''
Classify order with a validation set
'''

from examples.setup_client import setup_client
from src.rapidata.rapidata_client.feature_flags import FeatureFlags
from src.rapidata.rapidata_client.rapidata_client import RapidataClient
from src.rapidata.rapidata_client.workflow import ClassifyWorkflow
from src.rapidata.rapidata_client.referee import NaiveReferee
from src.rapidata.rapidata_client.metadata.prompt_metadata import PromptMetadata


def new_classify_order(rapi: RapidataClient):
    # Validation set
    validation_set = (
        rapi.new_validation_set("Example Validation Set")
        .add_classify_rapid(
            media_path="examples/data/wallaby.jpg",
            question="What kind of animal is this?",
            categories=["Mammal", "Marsupial", "Bird", "Reptile"],
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
        .validation_set_id(validation_set.id)
        .create()
    )

    result = order.get_status()
    print("Order in state: ", result.state)

    return order


if __name__ == "__main__":
    rapi = setup_client()
    order = new_classify_order(rapi)
