import unittest
from examples.setup_client import setup_client
from rapidata import MediaAsset, PromptMetadata, LabelingSelection
from rapidata.rapidata_client.workflow import EvaluationWorkflow


class TestExampleOrders(unittest.TestCase):

    def setUp(self):
        self.rapi = setup_client()

    def test_evaluation_order(self):
        # Validation set
        validation_set = (
            self.rapi.new_validation_set("Example Validation Set")
            .add_classify_rapid(
                asset=MediaAsset(path="examples/data/wallaby.jpg"),
                question="What kind of animal is this?",
                categories=["Fish", "Marsupial", "Bird", "Reptile"],
                truths=["Marsupial"],
                metadata=[PromptMetadata(prompt="Hint: It has a pouch")],
            )
            .create()
        )

        order = (
            self.rapi.new_order("Test Evaluation Order")
            .workflow(EvaluationWorkflow(validation_set_id=validation_set.id))
            .media([MediaAsset(path="examples/data/wallaby.jpg")])
            .selections([LabelingSelection(amount=1)])
            .create()
        )

        print("Done")