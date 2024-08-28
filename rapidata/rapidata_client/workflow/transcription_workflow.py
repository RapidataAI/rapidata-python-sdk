from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.api_client.models.transcription_rapid_blueprint import TranscriptionRapidBlueprint
from rapidata.rapidata_client.workflow.base_workflow import Workflow


class TranscriptionWorkflow(Workflow):

    def __init__(self, instruction: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._instruction = instruction
    
    def to_model(self) -> SimpleWorkflowModel:
        blueprint = TranscriptionRapidBlueprint(
            _t="TranscriptionBlueprint",
            title=self._instruction
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint)
        )