from abc import ABC, abstractmethod
from typing import Any

from rapidata.api_client.models.i_order_workflow_model import IOrderWorkflowModel
from rapidata.api_client.models.i_rapid_payload_classify_payload import (
    IRapidPayloadClassifyPayload,
)
from rapidata.api_client.models.i_rapid_payload_compare_payload import (
    IRapidPayloadComparePayload,
)
from rapidata.api_client.models.i_rapid_payload_locate_payload import (
    IRapidPayloadLocatePayload,
)
from rapidata.api_client.models.i_rapid_payload_scrub_payload import (
    IRapidPayloadScrubPayload,
)
from rapidata.api_client.models.i_rapid_payload_transcription_payload import (
    IRapidPayloadTranscriptionPayload,
)
from rapidata.api_client.models.i_rapid_payload_line_payload import (
    IRapidPayloadLinePayload,
)
from rapidata.api_client.models.i_rapid_payload_free_text_payload import (
    IRapidPayloadFreeTextPayload,
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
        IRapidPayloadClassifyPayload
        | IRapidPayloadComparePayload
        | IRapidPayloadLocatePayload
        | IRapidPayloadScrubPayload
        | IRapidPayloadLinePayload
        | IRapidPayloadFreeTextPayload
        | IRapidPayloadTranscriptionPayload
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
