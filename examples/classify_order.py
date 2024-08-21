from examples.setup_client import setup_client
from rapidata.rapidata_client.feature_flags import FeatureFlags
from rapidata.rapidata_client.rapidata_client import RapidataClient
from rapidata.rapidata_client.workflow import ClassifyWorkflow
from rapidata.rapidata_client.referee import NaiveReferee


def new_classify_order(rapi: RapidataClient):
    # Configure order
    order = (
        rapi.new_order(
            name="Example Classify Order",
        )
        .workflow(
            ClassifyWorkflow(
                question="Who should be president?",
                options=["Kamala Harris", "Donald Trump"],
            )
        )
        .media(["examples/data/kamala_trump.jpg"])
        .referee(NaiveReferee(required_guesses=15))
        .feature_flags(FeatureFlags().alert_on_fast_response(3))
        .create()
    )

    # order.approve() admin only: if it doesn't auto approve and you want to manually approve


if __name__ == "__main__":
    rapi = setup_client()
    new_classify_order(rapi)
