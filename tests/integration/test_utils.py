from unittest import TestCase

from examples.setup_client import setup_client


class TestUtils(TestCase):

    def setUp(self):
        self.rapi = setup_client()

    def test_creating_demographic_rapid(self):
        self.rapi.utils.new_demographic_rapid(
            identifier="age",
            question="How old are you?",
            options=["0-17", "18-29", "30-39", "40-49", "50-64", "65+"],
            media_path="examples/data/wallaby.jpg",
        )
