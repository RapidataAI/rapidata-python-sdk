from rapidata.api_client.models.evaluation_workflow_model import EvaluationWorkflowModel
from rapidata.rapidata_client.workflow.base_workflow import Workflow


class EvaluationWorkflow(Workflow):
    """Workflow to run evaluation orders. This is used internally only and should not be necessary to be used by clients."""

    def __init__(self, validation_set_id: str):
        super().__init__("EvaluationWorkflow")
        self.validation_set_id = validation_set_id

    def to_model(self):
        return EvaluationWorkflowModel(
            _t="EvaluationWorkflow", validationSetId=self.validation_set_id
        )
