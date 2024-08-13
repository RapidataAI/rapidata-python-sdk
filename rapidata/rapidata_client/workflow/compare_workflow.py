from typing import Any
from rapidata.rapidata_client.workflow import Workflow


class CompareWorkflow(Workflow):
    def __init__(self, criteria: str):
        super().__init__(type="CompareWorkflowConfig")
        self._criteria = criteria
        self._k_factor = 40
        self._match_size = 2
        self._matches_until_completed = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "criteria": self._criteria,
        }
    
    def k_factor(self, k_factor: int):
        self._k_factor = k_factor
        return self
    
    def match_size(self, match_size: int):
        self._match_size = match_size
        return self
    
    def matches_until_completed(self, matches_until_completed: int):
        self._matches_until_completed = matches_until_completed
        return self
    
