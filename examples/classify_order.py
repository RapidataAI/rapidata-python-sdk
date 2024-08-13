import dotenv
import os
dotenv.load_dotenv() # type: ignore

from rapidata.rapidata_client import RapidataClient
from rapidata.rapidata_client.workflow import FeatureFlags
from rapidata.rapidata_client.workflow import ClassifyWorkflow
from rapidata.rapidata_client.workflow.referee import NaiveReferee

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
ENDPOINT = os.getenv("ENDPOINT")

if not CLIENT_ID:
    raise Exception("CLIENT_ID not found in environment variables")

if not CLIENT_SECRET:
    raise Exception("CLIENT_SECRET not found in environment variables")

if not ENDPOINT:
    raise Exception("ENDPOINT not found in environment variables")

rapi = RapidataClient(
    client_id=CLIENT_ID, client_secret=CLIENT_SECRET, endpoint=ENDPOINT
)

# Configure order
order = (
    rapi.new_order(
        name="Example Classify Order",
    )
    .workflow(
        ClassifyWorkflow(
            question="Who should be president?",
            categories=["Kamala Harris", "Donald Trump"],
        )
        .referee(NaiveReferee(required_guesses=15))
        .feature_flags(FeatureFlags().alert_on_fast_response(3))
    )
    .create()
)

# Add data
order.dataset.add_images_from_paths(["examples/data/kamala_trump.jpg"])

# Let's go!
order.submit()
# order.approve() admin only: if it doesn't auto approve and you want to manually approve