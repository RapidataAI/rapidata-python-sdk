from typing import Any
from rapidata.api_client.models.attach_category_rapid_blueprint import AttachCategoryRapidBlueprint
from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.rapidata_client.workflow import Workflow


class ClassifyWorkflow(Workflow):
    """
    A workflow for classification tasks.

    This class represents a classification workflow where a question is presented
    along with a list of possible options for classification.

    Args:
        question (str): The classification question to be presented.
        options (list[str]): A list of possible classification options.

    Attributes:
        _question (str): The classification question.
        _options (list[str]): The list of classification options.
    """

    def __init__(self, question: str, options: list[str]):
        super().__init__(type="SimpleWorkflowConfig")
        self._question = question
        self._options = options

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "blueprint": {
                "_t": "ClassifyBlueprint",
                "title": self._question,
                "possibleCategories": self._options,
            }
        }

    def to_model(self) -> SimpleWorkflowModel:
        blueprint = AttachCategoryRapidBlueprint(
            _t="ClassifyBlueprint",
            title=self._question,
            possibleCategories=self._options,
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint),
        )
