from examples.setup_client import setup_client
from rapidata.rapidata_client.feature_flags.feature_flags import FeatureFlags
from rapidata.rapidata_client.rapidata_client import RapidataClient
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.workflow import CompareWorkflow


def new_compare_order(rapi: RapidataClient):
    logo_path = "examples/data/rapidata_logo.png"
    concept_path = "examples/data/rapidata_concept_logo.jpg"

    # configure validation set
    validation_set_id = rapi.new_validation_set(
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
                "examples/data/rapidata_concept_logo.jpg",
                "examples/data/rapidata_logo.png",
            ]
        )
        .validation_set(validation_set_id)
        .feature_flags(FeatureFlags().claire_design().alert_on_fast_response(4))
        .create()
    )

    return order


if __name__ == "__main__":
    rapi = setup_client()
    new_compare_order(rapi)
