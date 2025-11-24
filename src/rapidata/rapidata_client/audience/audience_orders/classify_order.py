from typing import Literal, cast
from rapidata.rapidata_client.datapoints._datapoints_validator import (
    DatapointsValidator,
)
from rapidata.rapidata_client.workflow import ClassifyWorkflow
from rapidata.rapidata_client.audience.audience_orders.audience_order import (
    AudienceOrder,
)


class ClassifyOrder(AudienceOrder):
    def __init__(
        self,
        name: str,
        instruction: str,
        answer_options: list[str],
        datapoints: list[str],
        data_type: Literal["media", "text"] = "media",
        responses_per_datapoint: int = 10,
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        private_notes: list[str] | None = None,
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
            workflow=ClassifyWorkflow(
                instruction=instruction, answer_options=answer_options
            ),
            datapoints=datapoint_instances,
            responses_per_datapoint=responses_per_datapoint,
        )
