from typing import Any
from src.rapidata_client.order.workflow.base_workflow import Workflow


class ClassifyWorkflow(Workflow):
    def __init__(self, question: str, categories: list[str]):
        super().__init__(type="SimpleWorkflowConfig")
        self._question = question
        self._categories = categories

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "blueprint": {
                "_t": "AttachCategoryRapidBlueprint",
                "title": self._question,
                "possibleCategories": self._categories,
            }
        }
