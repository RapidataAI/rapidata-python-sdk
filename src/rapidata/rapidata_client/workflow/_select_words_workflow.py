from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.api_client.models.transcription_rapid_blueprint import TranscriptionRapidBlueprint
from rapidata.rapidata_client.workflow._base_workflow import Workflow


class SelectWordsWorkflow(Workflow):
    """
    A workflow for select words tasks.

    This class represents a select words workflow where audio or video content
    is transcribed based on given instructions.

    Attributes:
        _instruction (str): The instruction for the select words task.

    Args:
        instruction (str): The instruction to be provided for the select words task.
    """

    def __init__(self, instruction: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._instruction = instruction

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = TranscriptionRapidBlueprint(
            _t="TranscriptionBlueprint",
            title=self._instruction
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint)
        )
