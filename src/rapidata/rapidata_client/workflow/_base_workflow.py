from abc import ABC, abstractmethod
from typing import Any

from rapidata.api_client.models.i_order_workflow_model import IOrderWorkflowModel
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
    def _to_model(self) -> IOrderWorkflowModel:
        pass

    def _format_datapoints(self, datapoints: list[Datapoint]) -> list[Datapoint]:
        return datapoints

    def __str__(self) -> str:
        return self._type

    def __repr__(self) -> str:
        return self._type
