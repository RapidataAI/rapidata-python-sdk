from typing import Any
from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_rapid_spec_compare_rapid_spec import (
    IRapidSpecCompareRapidSpec,
)
from rapidata.rapidata_client.workflow._rapid_spec import (
    ASSET,
    literal,
    simple_workflow,
)
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_compare_payload import (
    IRapidPayloadComparePayload,
)
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
    task_type = "Compare"

    def __init__(self, instruction: str, a_b_names: list[str] | None = None):
        super().__init__(type="CompareWorkflowConfig")
        self._validate_instruction(instruction)
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

    def _to_model(self) -> IOrderWorkflowInput:
        return simple_workflow(
            IRapidSpecCompareRapidSpec(
                _t="Compare",
                asset=ASSET,
                criteria=literal(self._instruction),
                indexIdentifiers=self._a_b_names,
            )
        )

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        return IRapidPayload(
            actual_instance=IRapidPayloadComparePayload(
                _t="ComparePayload",
                criteria=self._instruction,
            )
        )

    def __str__(self) -> str:
        return f"CompareWorkflow(instruction='{self._instruction}', a_b_names={self._a_b_names})"

    def __repr__(self) -> str:
        return f"CompareWorkflow(instruction={self._instruction!r}, a_b_names={self._a_b_names!r})"
