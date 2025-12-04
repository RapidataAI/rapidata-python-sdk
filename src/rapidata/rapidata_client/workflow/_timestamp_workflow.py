from rapidata.api_client.models.i_order_workflow_model import IOrderWorkflowModel
from rapidata.api_client.models.i_order_workflow_model_simple_workflow_model import (
    IOrderWorkflowModelSimpleWorkflowModel,
)
from rapidata.api_client.models.i_rapid_blueprint import IRapidBlueprint
from rapidata.api_client.models.i_rapid_blueprint_scrub_rapid_blueprint import (
    IRapidBlueprintScrubRapidBlueprint,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_scrub_payload import (
    IRapidPayloadScrubPayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.api_client.models.i_rapid_payload import IRapidPayload


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

    def __init__(self, instruction: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._instruction = instruction

    def _get_instruction(self) -> str:
        return self._instruction

    def _to_model(self) -> IOrderWorkflowModel:
        blueprint = IRapidBlueprintScrubRapidBlueprint(
            _t="ScrubBlueprint", target=self._instruction
        )

        return IOrderWorkflowModel(
            actual_instance=IOrderWorkflowModelSimpleWorkflowModel(
                _t="SimpleWorkflow",
                blueprint=IRapidBlueprint(actual_instance=blueprint),
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
