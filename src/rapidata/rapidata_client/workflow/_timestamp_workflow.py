from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_scrub_payload import (
    IRapidPayloadScrubPayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_rapid_spec_scrub_rapid_spec import (
    IRapidSpecScrubRapidSpec,
)
from rapidata.rapidata_client.workflow._rapid_spec import (
    ASSET,
    literal,
    simple_workflow,
)


class TimestampWorkflow(Workflow):
    """
    A workflow for timestamp tasks.

    This class represents a timestamp workflow
    where audio or video content receives timestamps based on the instruction.

    Attributes:
        _instruction (str): The instruction for the timestamp task.

    Args:
        instruction (str): The instruction to be provided for the timestamp task.
    """

    modality = RapidModality.SCRUB
    task_type = "Timestamp"

    def __init__(self, instruction: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._validate_instruction(instruction)
        self._instruction = instruction

    def _get_instruction(self) -> str:
        return self._instruction

    def _to_model(self) -> IOrderWorkflowInput:
        return simple_workflow(
            IRapidSpecScrubRapidSpec(
                _t="Scrub", asset=ASSET, target=literal(self._instruction)
            )
        )

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        return IRapidPayload(
            actual_instance=IRapidPayloadScrubPayload(
                _t="ScrubPayload",
                target=self._instruction,
            )
        )

    def __str__(self) -> str:
        return f"TimestampWorkflow(instruction='{self._instruction}')"

    def __repr__(self) -> str:
        return f"TimestampWorkflow(instruction={self._instruction!r})"
