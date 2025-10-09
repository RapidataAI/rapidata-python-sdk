from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.validation_set_zip_post_request_blueprint import (
    ValidationSetZipPostRequestBlueprint,
)
from rapidata.api_client.models.scrub_rapid_blueprint import ScrubRapidBlueprint
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client import ScrubPayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


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

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = ScrubRapidBlueprint(_t="ScrubBlueprint", target=self._instruction)

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=ValidationSetZipPostRequestBlueprint(blueprint),
        )

    def _to_payload(self, datapoint: Datapoint) -> ScrubPayload:
        return ScrubPayload(
            _t="ScrubPayload",
            target=self._instruction,
        )

    def __str__(self) -> str:
        return f"TimestampWorkflow(instruction='{self._instruction}')"

    def __repr__(self) -> str:
        return f"TimestampWorkflow(instruction={self._instruction!r})"
