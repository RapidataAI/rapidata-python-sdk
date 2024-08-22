import os
import unittest
from rapidata.rapidata_client.rapidata_client import RapidataClient
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.workflow.classify_workflow import ClassifyWorkflow
from rapidata.rapidata_client.workflow.feature_flags.feature_flags import FeatureFlags


class TestClassifyOrder(unittest.TestCase):

    def setUp(self):
        CLIENT_ID = os.getenv("CLIENT_ID")
        CLIENT_SECRET = os.getenv("CLIENT_SECRET")
        ENDPOINT = os.getenv("ENDPOINT")

        if not CLIENT_ID:
            raise Exception("CLIENT_ID not found in environment variables")
        if not CLIENT_SECRET:
            raise Exception("CLIENT_SECRET not found in environment variables")
        if not ENDPOINT:
            raise Exception("ENDPOINT not found in environment variables")

        self.rapi = RapidataClient(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET, endpoint=ENDPOINT
        )

    def test_classify_order(self):
        # Configure order
        order = (
            self.rapi.new_order(
                name="Example Classify Order",
            )
            .workflow(
                ClassifyWorkflow(
                    question="Who should be president?",
                    options=["Kamala Harris", "Donald Trump"],
                )
                .feature_flags(FeatureFlags().alert_on_fast_response(3))
            )
            .referee(NaiveReferee(required_guesses=15))
            .images(["examples/data/kamala_trump.jpg"])
            .create()
        )

        # Let's go!
        # order.approve()
