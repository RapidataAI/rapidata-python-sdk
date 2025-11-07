from typing import Any
from rapidata.api_client.models.attach_category_rapid_blueprint import (
    AttachCategoryRapidBlueprint,
)
from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.attach_category_rapid_blueprint_category import (
    AttachCategoryRapidBlueprintCategory,
)
from rapidata.api_client.models.simple_workflow_model_blueprint import (
    SimpleWorkflowModelBlueprint,
)
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client import ClassifyPayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.api_client.models.classify_payload_category import ClassifyPayloadCategory


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

    modality = RapidModality.CLASSIFY

    def __init__(self, instruction: str, answer_options: list[str]):
        super().__init__(type="SimpleWorkflowConfig")
        self._instruction = instruction
        self._answer_options = answer_options

    def _get_instruction(self) -> str:
        return self._instruction

    def _to_dict(self) -> dict[str, Any]:
        return {
            **super()._to_dict(),
            "blueprint": {
                "_t": "ClassifyBlueprint",
                "title": self._instruction,
                "possibleCategories": self._answer_options,
            },
        }

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = AttachCategoryRapidBlueprint(
            _t="ClassifyBlueprint",
            title=self._instruction,
            categories=[
                AttachCategoryRapidBlueprintCategory(label=option, value=option)
                for option in self._answer_options
            ],
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint),
        )

    def _to_payload(self, datapoint: Datapoint) -> ClassifyPayload:
        return ClassifyPayload(
            _t="ClassifyPayload",
            categories=[
                ClassifyPayloadCategory(label=option, value=option)
                for option in self._answer_options
            ],
            title=self._instruction,
        )

    def __str__(self) -> str:
        return f"ClassifyWorkflow(instruction='{self._instruction}', options={self._answer_options})"

    def __repr__(self) -> str:
        return f"ClassifyWorkflow(instruction='{self._instruction}', answer_options={self._answer_options!r})"
