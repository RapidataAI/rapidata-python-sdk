import unittest
from unittest.mock import Mock

from rapidata.rapidata_client.order.rapidata_order import RapidataOrder

class TestOrder(unittest.TestCase):

    def setUp(self):
        self.rapidata_service = Mock()
        self.rapidata_service.order = Mock()
        self.rapidata_service.order.create_order.return_value = ("order_id", "dataset_id")
        self.workflow = Mock()
        # create mock to_dict function
        self.workflow.to_dict.return_value = {"workflow": "data"}
        self.order_name = "test order"

    def test_submit(self):
        order = RapidataOrder(self.order_name, self.workflow, self.rapidata_service).create()
        order.submit()

        self.rapidata_service.order.create_order.assert_called_with(self.order_name, self.workflow.to_dict())
        self.rapidata_service.order.submit.assert_called_with(order.order_id)
        self.assertEqual(order.order_id, "order_id")
