from typing import Literal
from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.rapidata_client.settings import RapidataSetting
from typing import Sequence
from rapidata.api_client.models.compare_payload import (
    ComparePayload,
)
from rapidata.api_client.models.compare_truth import CompareTruth


class CompareRapid(Rapid):
    def __init__(
        self,
        instruction: str,
        datapoint: list[str],
        truth: str,
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ):
        if len(datapoint) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        if truth not in datapoint:
            raise ValueError("Truth is not one of the datapoints")

        super().__init__(
            asset=datapoint,
            data_type=data_type,
            context=context,
            media_context=media_context,
            explanation=explanation,
            payload=ComparePayload(
                _t="ComparePayload",
                criteria=instruction,
            ),
            truth=CompareTruth(winnerId=truth, _t="CompareTruth"),
            random_correct_probability=0.5,
            settings=settings,
        )
