import unittest
from examples.classify_order import new_classify_order
from examples.compare_order import new_compare_order
from examples.free_text_order import new_free_text_order
from examples.setup_client import setup_client
import time

from rapidata.rapidata_client.order.dataset.rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder

class TestClassifyOrder(unittest.TestCase):

    def setUp(self):
        self.rapi = setup_client()

    def test_classify_order(self):
        new_classify_order(self.rapi)

    def test_free_text_input_order(self):
        new_free_text_order(self.rapi)

    def test_compare_order(self):
        new_compare_order(self.rapi)

    def test_get_results(self):
        # time.sleep(1)
        # order.approve()
        # order.wait_for_done()
        # order.get_results()
        pass

    