from typing import Any
from rapidata.rapidata_client.workflow import Workflow


class FreeTextWorkflow(Workflow):
    def __init__(self, question: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._question = question

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "blueprint": {
                "_t": "FreeTextBlueprint",
                "question": self._question,
            },
        }
