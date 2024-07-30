import unittest
from unittest.mock import Mock

from src.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from src.rapidata_client.order.referee.naive_referee import NaiveReferee


class TestOrderBuilder(unittest.TestCase):
    def setUp(self):
        self.order_service = Mock()

    def test_basic_order_creation(self):
        order = RapidataOrderBuilder(
            order_service=self.order_service,
            name="Test Order",
            question="What is the capital of France?",
            categories=["Berlin", "Paris", "London"],
        ).create()

        self.assertEqual(order.config.name, "Test Order")
        self.assertEqual(order.config.question, "What is the capital of France?")
        self.assertEqual(order.config.categories, ["Berlin", "Paris", "London"])

    def test_adding_referee(self):
        order = (
            RapidataOrderBuilder(
                order_service=self.order_service,
                name="Test Order",
                question="What is the capital of France?",
                categories=["Berlin", "Paris", "London"],
            )
            .referee(NaiveReferee(required_guesses=15))
            .create()
        )

        # check type of referee is SimpleReferee
        if not isinstance(order.config.referee, NaiveReferee):
            raise AssertionError("Referee is not of type SimpleReferee")

        self.assertEqual(order.config.referee.required_guesses, 15)
