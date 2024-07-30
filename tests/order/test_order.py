import unittest
from unittest.mock import Mock

from src.rapidata_client.order.rapidata_order import RapidataOrder

class TestOrder(unittest.TestCase):

    def setUp(self):
        self.order_service = Mock()
        self.order_service.create_order.return_value = ("order_id", "dataset_id")

        self.config = Mock()

    def test_submit(self):
        order = RapidataOrder(self.config, self.order_service)
        order.submit()

        self.order_service.create_order.assert_called_with(self.config)
        self.order_service.submit.assert_called_with(order.order_id)
        self.assertEqual(order.order_id, "order_id")
