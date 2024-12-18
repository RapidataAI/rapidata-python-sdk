from rapidata.api_client.models.evaluation_workflow_model import EvaluationWorkflowModel
from rapidata.rapidata_client.workflow._base_workflow import Workflow


class EvaluationWorkflow(Workflow):
    """
    A workflow to run evaluation orders.

    This is used internally only and should not be necessary to be used by clients.
    
    Args:
        validation_set_id (str): a source for the tasks that will be sent to the user
        should_accept_incorrect (bool): indicates if the user should get feedback on their answers if they answer wrong. If set to true the user will not notice that he was tested.
    """

    def __init__(self, validation_set_id: str, should_accept_incorrect: bool):
        super().__init__("EvaluationWorkflow")
        self.validation_set_id = validation_set_id
        self.should_accept_incorrect = should_accept_incorrect

    def _to_model(self):
        return EvaluationWorkflowModel(
            _t="EvaluationWorkflow",
            validationSetId=self.validation_set_id,
            shouldAcceptIncorrect=self.should_accept_incorrect,
        )
