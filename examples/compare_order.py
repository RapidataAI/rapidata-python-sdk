from examples.setup_client import setup_client
from rapidata.rapidata_client.rapidata_client import RapidataClient
from rapidata.rapidata_client.workflow import CompareWorkflow


def new_compare_order(rapi: RapidataClient):
    order = (
        rapi.new_order(
            name="Example Compare Order",
        )
        .workflow(
            CompareWorkflow(
                criteria="Who should be president?",
            )
            .matches_until_completed(5)
            .match_size(2)
        )
        .media(media_paths=["examples/data/kamala.jpg", "examples/data/trump.jpg"])
        .create()
    )

if __name__ == "__main__":
    rapi = setup_client()
    new_compare_order(rapi)
