from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.api_client.models.line_rapid_blueprint import LineRapidBlueprint
from rapidata.rapidata_client.workflow._base_workflow import Workflow


class DrawWorkflow(Workflow):

    def __init__(self, target: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._target = target

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = LineRapidBlueprint(
            _t="LineBlueprint",
            target=self._target
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint)
        )
