import unittest

from src.rapidata_client.order.referee.naive_referee import NaiveReferee
from src.rapidata_client.rapidata_client import RapidataClient


class TestRapidataClient(unittest.TestCase):
    def test_basic_order_creation(self):
        rapi = RapidataClient(api_key="test")
        order = (
            rapi.new_order(
                name="Test Order",
                question="What is the capital of France?",
                categories=["Berlin", "Paris", "London"],
            )
            .referee(NaiveReferee(required_guesses=15))
            .create()
        )

        self.assertEqual(order.config.name, "Test Order")
        self.assertEqual(order.config.question, "What is the capital of France?")
        self.assertEqual(order.config.categories, ["Berlin", "Paris", "London"])
