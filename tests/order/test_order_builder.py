import unittest
from unittest.mock import MagicMock, Mock

from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.workflow import ClassifyWorkflow


class TestOrderBuilder(unittest.TestCase):
    def setUp(self):
        # Create a mock for the result of order_create_post
        mock_result = MagicMock()
        mock_result.order_id = "test_order_123"
        mock_result.dataset_id = "test_dataset_456"

        # Create a mock for the order_api
        mock_order_api = Mock()
        mock_order_api.order_create_post.return_value = mock_result

        # Create a mock for the openapi_service
        self.mock_openapi_service = Mock()
        self.mock_openapi_service.order_api = mock_order_api


    def test_raise_error_if_no_workflow(self):
        with self.assertRaises(ValueError):
            RapidataOrderBuilder(
                openapi_service=self.mock_openapi_service, name="Test Order"
            ).create()

    def test_basic_order_build(self):
        order_builder = (
            RapidataOrderBuilder(
                openapi_service=self.mock_openapi_service, name="Test Order"
            )
            .workflow(
                ClassifyWorkflow(question="Test Question?", options=["Yes", "No"])
            )
        )

        self.assertEqual(order_builder._name, "Test Order")
        self.assertIsInstance(order_builder._workflow, ClassifyWorkflow)

        self.assertEqual(order_builder._workflow._question, "Test Question?")  # type: ignore
        self.assertEqual(order_builder._workflow._options, ["Yes", "No"])  # type: ignore
