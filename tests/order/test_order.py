import unittest
from unittest.mock import Mock

from src.rapidata_client.order.rapidata_order import RapidataOrder

class TestOrder(unittest.TestCase):

    def setUp(self):
        self.rapidata_service = Mock()
        self.rapidata_service.order = Mock()
        self.rapidata_service.order.create_order.return_value = ("order_id", "dataset_id")
        self.config = Mock()

    def test_submit(self):
        order = RapidataOrder(self.config, self.rapidata_service).create()
        order.submit()

        self.rapidata_service.order.create_order.assert_called_with(self.config)
        self.rapidata_service.order.submit.assert_called_with(order.order_id)
        self.assertEqual(order.order_id, "order_id")
