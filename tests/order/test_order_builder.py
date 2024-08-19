import unittest
from unittest.mock import Mock

from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.workflow import ClassifyWorkflow


class TestOrderBuilder(unittest.TestCase):
    def setUp(self):
        self.api_client = Mock()
        self.api_client.order = Mock()
        self.api_client.order.create_order.return_value = ("order_id", "dataset_id")

    def test_raise_error_if_no_workflow(self):

        with self.assertRaises(ValueError):
            RapidataOrderBuilder(api_client=self.api_client, name="Test Order").create()

    def test_basic_order_build(self):
        order = (
            RapidataOrderBuilder(api_client=self.api_client, name="Test Order")
            .workflow(
                ClassifyWorkflow(question="Test Question?", options=["Yes", "No"])
            )
            .create()
        )

        self.assertEqual(order.name, "Test Order")
        self.assertIsInstance(order.workflow, ClassifyWorkflow)

        self.assertEqual(order.workflow._question, "Test Question?")  # type: ignore
        self.assertEqual(order.workflow._categories, ["Yes", "No"])  # type: ignore
