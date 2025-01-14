from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.api_client.models.scrub_rapid_blueprint import ScrubRapidBlueprint
from rapidata.rapidata_client.workflow._base_workflow import Workflow


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

    def __init__(self, instruction: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._instruction = instruction

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = ScrubRapidBlueprint(
            _t="ScrubBlueprint",
            target=self._instruction
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint)
        )
