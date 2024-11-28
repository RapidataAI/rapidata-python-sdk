from typing import Any
from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client.models.free_text_rapid_blueprint import FreeTextRapidBlueprint


class FreeTextWorkflow(Workflow):
    """
    A workflow for free text input tasks.

    This class represents a workflow where users can provide free-form text responses
    to a given question.

    Attributes:
        _question (str): The question to be answered with free text.

    Args:
        question (str): The question to be presented for free text input.
    """

    def __init__(self, question: str):
        """
        Initialize a FreeTextWorkflow instance.

        Args:
            question (str): The question to be presented for free text input.
        """
        super().__init__(type="SimpleWorkflowConfig")
        self._question = question

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "blueprint": {
                "_t": "FreeTextBlueprint",
                "question": self._question,
            },
        }

    def to_model(self) -> SimpleWorkflowModel:
        blueprint = FreeTextRapidBlueprint(
            _t="FreeTextBlueprint",
            question=self._question,
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint),
        )
