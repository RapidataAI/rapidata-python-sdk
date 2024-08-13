import unittest
from unittest.mock import Mock

from src.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from src.rapidata_client.order.workflow.classify_workflow import ClassifyWorkflow


class TestOrderBuilder(unittest.TestCase):
    def setUp(self):
        self.rapidata_service = Mock()
        self.rapidata_service.order = Mock()
        self.rapidata_service.order.create_order.return_value = ("order_id", "dataset_id")

    def test_raise_error_if_no_workflow(self):

        with self.assertRaises(ValueError):
            RapidataOrderBuilder(rapidata_service=self.rapidata_service, name="Test Order").create()

    def test_basic_order_build(self):
        order = (
            RapidataOrderBuilder(
                rapidata_service=self.rapidata_service, name="Test Order"
            )
            .workflow(ClassifyWorkflow(question="Test Question?", categories=["Yes", "No"]))
            .create()
        )

        self.assertEqual(order.name, "Test Order")
        self.assertIsInstance(order.workflow, ClassifyWorkflow)

        self.assertEqual(order.workflow._question, "Test Question?") # type: ignore
        self.assertEqual(order.workflow._categories, ["Yes", "No"]) # type: ignore
        