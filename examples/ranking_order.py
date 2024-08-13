import dotenv
import os
dotenv.load_dotenv() # type: ignore

from rapidata.rapidata_client import RapidataClient
from rapidata.rapidata_client.workflow import CompareWorkflow

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

order = rapi.new_order(
    name="Example Compare Order",
).workflow(
    CompareWorkflow(
        criteria="Who should be president?",
    )
    .matches_until_completed(5)
    .match_size(2)
).create()

order.dataset.add_images_from_paths(["examples/data/kamala.jpg", "examples/data/trump.jpg"])

order.submit()
# order.approve()