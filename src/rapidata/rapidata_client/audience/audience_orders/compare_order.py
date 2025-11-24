from typing import Literal, Sequence
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.workflow._compare_workflow import CompareWorkflow
from rapidata.rapidata_client.audience.audience_orders.audience_order import (
    AudienceOrder,
)
from rapidata.rapidata_client.settings import RapidataSetting


class CompareOrder(AudienceOrder):
    def __init__(
        self,
        name: str,
        instruction: str,
        datapoints: list[list[str]],
        data_type: Literal["media", "text"] = "media",
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        a_b_names: list[str] | None = None,
        private_notes: list[str] | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ):
        datapoint_instances = DatapointsValidator.map_datapoints(
            datapoints=datapoints,
            contexts=contexts,
            media_contexts=media_contexts,
            private_notes=private_notes,
            data_type=data_type,
        )
        super().__init__(
            name=name,
            workflow=CompareWorkflow(instruction=instruction, a_b_names=a_b_names),
            datapoints=datapoint_instances,
            responses_per_datapoint=responses_per_datapoint,
            settings=settings,
        )
