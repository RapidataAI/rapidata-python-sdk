from typing import Any
from rapidata.api_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client.models.compare_rapid_blueprint import CompareRapidBlueprint
from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel


class CompareWorkflow(Workflow):
    def __init__(self, criteria: str):
        super().__init__(type="CompareWorkflowConfig")
        self._criteria = criteria

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "criteria": self._criteria,
        }
    
    def to_model(self) -> SimpleWorkflowModel:
        blueprint = CompareRapidBlueprint(
            _t="CompareBlueprint",
            criteria=self._criteria,
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint),
        )
    
