from abc import ABC, abstractmethod
from typing import Any

from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.evaluation_workflow_model import EvaluationWorkflowModel
from rapidata.api_client.models.compare_workflow_model import CompareWorkflowModel
from rapidata.rapidata_client.referee._base_referee import Referee


class Workflow(ABC):

    def __init__(self, type: str):
        self._type = type
        self._target_country_codes: list[str] = []

    def _to_dict(self) -> dict[str, Any]:
        return {
            "_t": self._type,
        }

    @abstractmethod
    def _to_model(
        self,
    ) -> SimpleWorkflowModel | CompareWorkflowModel | EvaluationWorkflowModel:
        pass
