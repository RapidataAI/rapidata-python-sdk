'''
Compare order with a validation set
'''

from examples.setup_client import setup_client
from src.rapidata.rapidata_client.feature_flags import FeatureFlags
from src.rapidata.rapidata_client.rapidata_client import RapidataClient
from src.rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from src.rapidata.rapidata_client.workflow import CompareWorkflow


def new_compare_order(rapi: RapidataClient):
    logo_path = "examples/data/rapidata_logo.png"
    concept_path = "examples/data/rapidata_concept_logo.jpg"

    # configure validation set
    validation_set = rapi.new_validation_set(
        name="Example SimpleMatchup Validation Set"
    ).add_compare_rapid(
        media_paths=[logo_path, concept_path],
        question="Which logo is the actual Rapidata logo?",
        truth=logo_path,
    ).create()

    # configure order
    order = (
        rapi.new_order(
            name="Example SimpleMatchup Order",
        )
        .workflow(
            CompareWorkflow(
                criteria="Which logo is better?",
            )
        )
        .referee(NaiveReferee(required_guesses=1))
        .media(
            media_paths=[
                [  # this is a list of lists of paths, since each rapid shows two images
                    "examples/data/rapidata_concept_logo.jpg",
                    "examples/data/rapidata_logo.png",
                ]
            ]
        )
        .validation_set_id(validation_set.id)
        .feature_flags(
            FeatureFlags().compare_with_prompt_design().alert_on_fast_response(4000)
        )
        .create()
    )

    return order


if __name__ == "__main__":
    rapi = setup_client()
    new_compare_order(rapi)
