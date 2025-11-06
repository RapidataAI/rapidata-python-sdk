from typing import Any
from rapidata.api_client.models.simple_workflow_model_blueprint import (
    SimpleWorkflowModelBlueprint,
)
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client.models.compare_rapid_blueprint import CompareRapidBlueprint
from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client import ComparePayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


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

    modality = RapidModality.COMPARE

    def __init__(self, instruction: str, a_b_names: list[str] | None = None):
        super().__init__(type="CompareWorkflowConfig")
        self._instruction = instruction
        self._a_b_names = a_b_names

    def _get_instruction(self) -> str:
        return self._instruction

    def _to_dict(self) -> dict[str, Any]:
        return {
            **super()._to_dict(),
            "criteria": self._instruction,
            "indexIdentifiers": self._a_b_names,
        }

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = CompareRapidBlueprint(
            _t="CompareBlueprint",
            criteria=self._instruction,
            indexIdentifiers=self._a_b_names,
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint),
        )

    def _to_payload(self, datapoint: Datapoint) -> ComparePayload:
        return ComparePayload(
            _t="ComparePayload",
            criteria=self._instruction,
        )

    def __str__(self) -> str:
        return f"CompareWorkflow(instruction='{self._instruction}', a_b_names={self._a_b_names})"

    def __repr__(self) -> str:
        return f"CompareWorkflow(instruction={self._instruction!r}, a_b_names={self._a_b_names!r})"
