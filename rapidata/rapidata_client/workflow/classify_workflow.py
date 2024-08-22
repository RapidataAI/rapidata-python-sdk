from typing import Any
from openapi_client.models.attach_category_rapid_blueprint import AttachCategoryRapidBlueprint
from openapi_client.models.simple_workflow_model import SimpleWorkflowModel
from openapi_client.models.simple_workflow_model_blueprint import SimpleWorkflowModelBlueprint
from rapidata.rapidata_client.workflow import Workflow


class ClassifyWorkflow(Workflow):
    def __init__(self, question: str, options: list[str]):
        super().__init__(type="SimpleWorkflowConfig")
        self._question = question
        self._options = options

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "blueprint": {
                "_t": "ClassifyBlueprint",
                "title": self._question,
                "possibleCategories": self._options,
            }
        }

    def to_model(self) -> SimpleWorkflowModel:
        blueprint = AttachCategoryRapidBlueprint(
            _t="ClassifyBlueprint",
            title=self._question,
            possibleCategories=self._options,
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint),
        )
