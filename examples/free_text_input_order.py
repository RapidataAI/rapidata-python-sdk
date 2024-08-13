import dotenv
import os
dotenv.load_dotenv() # type: ignore

from rapidata.rapidata_client import RapidataClient
from rapidata.rapidata_client.workflow import FeatureFlags
from rapidata.rapidata_client.workflow import FreeTextWorkflow
from rapidata.rapidata_client.workflow.country_codes import CountryCodes

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
        name="Example Video Free Text Order",
    ).workflow(
        FreeTextWorkflow(
            question="Describe the movement in this video!",
        ).feature_flags(
            FeatureFlags().free_text_minimum_characters(15).alert_on_fast_response(5)
        ).target_country_codes(CountryCodes.ENGLISH_SPEAKING)
    ).create()

order.dataset.add_videos_from_paths([""]) # TODO: insert video path
order.submit()