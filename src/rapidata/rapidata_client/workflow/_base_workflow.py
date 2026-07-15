from abc import ABC, abstractmethod
from typing import Any

from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


class Workflow(ABC):
    modality: RapidModality

    # SDK public task-type name used to filter task-type-aware settings.
    # ``None`` means the workflow has no rapid task type (e.g. evaluation) and
    # is never checked. Keep the values in sync with the settings support matrix
    # mirrored across the other two repos (rapids-frontend / app-frontend).
    task_type: str | None = None

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
    ) -> IRapidPayload:
        pass

    @abstractmethod
    def _get_instruction(self) -> str:
        pass

    @abstractmethod
    def _to_model(self) -> IOrderWorkflowInput:
        pass

    def _format_datapoints(self, datapoints: list[Datapoint]) -> list[Datapoint]:
        return datapoints

    def __str__(self) -> str:
        return self._type

    def __repr__(self) -> str:
        return self._type
