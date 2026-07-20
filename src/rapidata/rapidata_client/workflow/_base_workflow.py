from abc import ABC, abstractmethod
from typing import Any

from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality

MAX_INSTRUCTION_LENGTH: int = 250


def validate_instruction_length(
    instruction: str, max_length: int = MAX_INSTRUCTION_LENGTH
) -> None:
    """Raise ``ValueError`` if ``instruction`` is longer than ``max_length``.

    Shared by the workflow base class and the audience example handler so the
    limit (and its message) live in exactly one place. The limit mirrors the
    backend's unified instruction limit across all SDK-reachable task types.
    """
    if len(instruction) > max_length:
        raise ValueError(
            f"instruction is {len(instruction)} characters; maximum is {max_length}"
        )


class Workflow(ABC):
    modality: RapidModality

    MAX_INSTRUCTION_LENGTH: int = MAX_INSTRUCTION_LENGTH

    # SDK public task-type name used to filter task-type-aware settings.
    # ``None`` means the workflow has no rapid task type (e.g. evaluation) and
    # is never checked. Keep the values in sync with the settings support matrix
    # mirrored across the other two repos (rapids-frontend / app-frontend).
    task_type: str | None = None

    def __init__(self, type: str):
        self._type = type

    def _validate_instruction(self, instruction: str) -> None:
        validate_instruction_length(instruction, self.MAX_INSTRUCTION_LENGTH)

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
