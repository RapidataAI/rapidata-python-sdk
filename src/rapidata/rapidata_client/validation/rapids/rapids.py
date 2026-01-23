from __future__ import annotations

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting
from typing import Literal, Sequence
from pydantic import BaseModel, model_validator, ConfigDict
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_validation_truth_model import IValidationTruthModel


class Rapid(BaseModel):
    asset: str | list[str]
    payload: IRapidPayload
    data_type: Literal["media", "text"] = "media"
    truth: IValidationTruthModel | None = None
    context: str | None = None
    media_context: str | None = None
    sentence: str | None = None
    random_correct_probability: float | None = None
    explanation: str | None = None
    settings: Sequence[RapidataSetting] | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True, populate_by_name=True, extra="allow"
    )

    @model_validator(mode="after")
    def check_sentence_and_context(self) -> Rapid:
        if isinstance(self.sentence, str) and isinstance(self.context, str):
            raise ValueError(
                "Both 'sentence' and 'context' cannot be strings at the same time."
            )
        return self
