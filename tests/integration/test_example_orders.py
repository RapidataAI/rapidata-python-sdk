import time
import unittest
from examples.classify_order import new_classify_order
from examples.compare_order import new_compare_order
from examples.free_text_order import new_free_text_order
from examples.setup_client import setup_client
from examples.transcription_order import new_transcription_order
from examples.classify_text_asset_order import new_classify_text_asset_order
from examples.conditional_validation_rapid_selection import (
    new_cond_validation_rapid_order,
)


class TestExampleOrders(unittest.TestCase):

    def setUp(self):
        self.rapi = setup_client()

    def test_classify_order(self):
        new_classify_order(self.rapi)

    def test_classify_text_asset_order(self):
        new_classify_text_asset_order(self.rapi)

    def test_free_text_input_order(self):
        new_free_text_order(self.rapi)

    def test_compare_order(self):
        new_compare_order(self.rapi)

    def test_transcription_order(self):
        new_transcription_order(self.rapi)

    def test_cond_validation_order(self):
        new_cond_validation_rapid_order(self.rapi)

    def test_get_results(self):
        # order = new_classify_order(self.rapi)
        # time.sleep(1)
        # order.approve()
        # order.wait_for_done()
        # order.get_results()
        pass

    def test_quickstart(self):
        import dotenv
        import os

        dotenv.load_dotenv()

        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")
        ENDPOINT = os.getenv("ENDPOINT")

        if not CLIENT_ID or not CLIENT_SECRET or not ENDPOINT:
            raise ValueError(
                "Please set CLIENT_ID, CLIENT_SECRET, and ENDPOINT in a .env file"
            )

        from rapidata.rapidata_client import RapidataClient

        rapi = RapidataClient(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET, endpoint=ENDPOINT
        )

        order_builder = rapi.new_order("Example Order")

        from rapidata.rapidata_client.workflow import ClassifyWorkflow

        workflow = ClassifyWorkflow(
            question="What is shown in the image?",
            options=["Fish", "Cat", "Wallaby", "Airplane"],
        )

        order_builder.workflow(workflow)

        from rapidata.rapidata_client.referee import NaiveReferee

        order_builder.referee(NaiveReferee(required_guesses=15))

        order_builder.media(["examples/data/wallaby.jpg"])
