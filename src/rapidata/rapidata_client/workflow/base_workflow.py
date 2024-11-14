from abc import ABC, abstractmethod
from typing import Any

from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.evaluation_workflow_model import EvaluationWorkflowModel
from rapidata.api_client.models.compare_workflow_model import CompareWorkflowModel
from rapidata.rapidata_client.settings import Settings
from rapidata.rapidata_client.referee.base_referee import Referee


class Workflow(ABC):

    def __init__(self, type: str):
        self._type = type
        self._target_country_codes: list[str] = []
        self._feature_flags: Settings = Settings()

    def to_dict(self) -> dict[str, Any]:
        return {
            "_t": self._type,
            "referee": self._referee.to_dict(),
            "targetCountryCodes": self._target_country_codes,
            "featureFlags": self._feature_flags.to_list(),
        }

    @abstractmethod
    def to_model(
        self,
    ) -> SimpleWorkflowModel | CompareWorkflowModel | EvaluationWorkflowModel:
        pass

    def referee(self, referee: Referee):
        self._referee = referee
        return self

    def target_country_codes(self, target_country_codes: list[str]):
        self._target_country_codes = target_country_codes
        return self

    def feature_flags(self, feature_flags: Settings):
        self._feature_flags = feature_flags
        return self
