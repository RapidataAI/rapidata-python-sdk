from examples.setup_client import setup_client
from rapidata.rapidata_client.rapidata_client import RapidataClient
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.workflow import CompareWorkflow


def new_compare_order(rapi: RapidataClient):
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
        .create()
    )

    return order

if __name__ == "__main__":
    rapi = setup_client()
    new_compare_order(rapi)
