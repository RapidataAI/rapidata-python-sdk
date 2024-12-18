from typing import Any
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client.models.compare_rapid_blueprint import CompareRapidBlueprint
from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel


class CompareWorkflow(Workflow):
    """
    A workflow for comparison tasks.

    This class represents a comparison workflow where items are compared based on
    specified instruction.

    Attributes:
        _instruction (str): The instruction used for comparison.

    Args:
        instruction (str): The instruction to be used for comparison.
    """

    def __init__(self, instruction: str):
        super().__init__(type="CompareWorkflowConfig")
        self._instruction = instruction

    def _to_dict(self) -> dict[str, Any]:
        return {
            **super()._to_dict(),
            "criteria": self._instruction,
        }

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = CompareRapidBlueprint(
            _t="CompareBlueprint",
            criteria=self._instruction,
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint),
        )
