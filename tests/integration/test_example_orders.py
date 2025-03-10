import time
import unittest
from rapidata import RapidataClient
from examples.classify_order import get_emotions_of_images_order
from examples.compare_order import new_compare_order
from examples.free_text_order import get_prompt_ideas
import examples.select_words_order as select_words_order
from examples.classify_text_asset_order import new_classify_text_asset_order
from examples.conditional_validation_rapid_selection import (
    new_cond_validation_rapid_order,
)


class TestExampleOrders(unittest.TestCase):

    def setUp(self):
        self.rapi = RapidataClient()

    def test_classify_order(self):
        get_emotions_of_images_order(self.rapi)

    def test_classify_text_asset_order(self):
        new_classify_text_asset_order(self.rapi)

    def test_free_text_input_order(self):
        get_prompt_ideas(self.rapi)

    def test_compare_order(self):
        new_compare_order(self.rapi)

    def test_transcription_order(self):
        validation_set = select_words_order.create_validation_set(self.rapi)
        select_words_order.new_select_words_order(self.rapi, validation_set.id)

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
        CERT_PATH = os.getenv("CERT_PATH")
        TOKEN_URL = os.getenv("TOKEN_URL")

        if not CLIENT_ID or not CLIENT_SECRET or not ENDPOINT or not TOKEN_URL:
            raise ValueError(
                "Please set CLIENT_ID, CLIENT_SECRET, and ENDPOINT in a .env file"
            )

        from rapidata.rapidata_client import RapidataClient

        rapi = RapidataClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            endpoint=ENDPOINT,
            cert_path=CERT_PATH,
            token_url=TOKEN_URL,
        )

        order_builder = rapi.new_order("Example Order")

        from rapidata.rapidata_client.workflow import ClassifyWorkflow

        workflow = ClassifyWorkflow(
            question="What is shown in the image?",
            options=["Fish", "Cat", "Wallaby", "Airplane"],
        )

        order_builder.workflow(workflow)

        from rapidata import NaiveReferee, MediaAsset

        order_builder.referee(NaiveReferee(responses=15))

        order_builder.media([MediaAsset("examples/data/wallaby.jpg")])
