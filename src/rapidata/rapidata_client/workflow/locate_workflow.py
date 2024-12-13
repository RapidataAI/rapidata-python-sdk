from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.api_client.models.locate_rapid_blueprint import LocateRapidBlueprint
from rapidata.rapidata_client.workflow._base_workflow import Workflow


class LocateWorkflow(Workflow):

    def __init__(self, target: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._target = target

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = LocateRapidBlueprint(
            _t="LocateBlueprint",
            target=self._target
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint)
        )
