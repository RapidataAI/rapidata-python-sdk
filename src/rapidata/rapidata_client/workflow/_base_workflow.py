from abc import ABC, abstractmethod
from typing import Any

from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.evaluation_workflow_model import EvaluationWorkflowModel
from rapidata.api_client.models.compare_workflow_model import CompareWorkflowModel
from rapidata.api_client.models.grouped_ranking_workflow_model import (
    GroupedRankingWorkflowModel,
)
from rapidata.api_client import (
    ClassifyPayload,
    ComparePayload,
    LocatePayload,
    ScrubPayload,
    TranscriptionPayload,
    LinePayload,
    FreeTextPayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


class Workflow(ABC):
    modality: RapidModality

    def __init__(self, type: str):
        self._type = type

    def _to_dict(self) -> dict[str, Any]:
        return {
            "_t": self._type,
        }

    @abstractmethod
    def _to_payload(
        self,
        datapoint: Datapoint,
    ) -> (
        ClassifyPayload
        | ComparePayload
        | LocatePayload
        | ScrubPayload
        | LinePayload
        | FreeTextPayload
        | TranscriptionPayload
    ):
        pass

    @abstractmethod
    def _get_instruction(self) -> str:
        pass

    @abstractmethod
    def _to_model(
        self,
    ) -> (
        SimpleWorkflowModel
        | CompareWorkflowModel
        | EvaluationWorkflowModel
        | GroupedRankingWorkflowModel
    ):
        pass

    def _format_datapoints(self, datapoints: list[Datapoint]) -> list[Datapoint]:
        return datapoints

    def __str__(self) -> str:
        return self._type

    def __repr__(self) -> str:
        return self._type
