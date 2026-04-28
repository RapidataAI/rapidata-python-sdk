from __future__ import annotations

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting
from rapidata.rapidata_client.config import logger
from typing import Literal, Sequence
from pydantic import BaseModel, model_validator, field_validator, ConfigDict
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_validation_truth_model import IValidationTruthModel


class Rapid(BaseModel):
    asset: str | list[str]
    payload: IRapidPayload
    data_type: Literal["media", "text"] = "media"
    truth: IValidationTruthModel | None = None
    context: str | None = None
    media_context: list[str] | None = None
    sentence: str | None = None
    random_correct_probability: float | None = None
    explanation: str | None = None
    settings: Sequence[RapidataSetting] | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True, populate_by_name=True, extra="allow"
    )

    @field_validator("media_context", mode="before")
    @classmethod
    def media_context_normalize(cls, v: object) -> list[str] | None:
        """Always store media_context as a list of strings.

        Accepts ``str`` for backward compatibility — emits a deprecation
        warning and wraps it in a single-element list so the rest of the
        SDK only ever has to deal with ``list[str]``.
        """
        if v is None:
            return None
        if isinstance(v, str):
            if v == "":
                raise ValueError(
                    "media_context cannot be an empty string. If not needed, set to None."
                )
            logger.warning(
                "Passing a string for media_context is deprecated; pass a list of strings instead. "
                "Wrapping the value in a single-element list."
            )
            return [v]
        if isinstance(v, list):
            if len(v) == 0:
                raise ValueError(
                    "media_context cannot be an empty list. If not needed, set to None."
                )
            if any(not isinstance(item, str) or item == "" for item in v):
                raise ValueError(
                    "Every entry in a media_context list must be a non-empty string."
                )
            return v
        raise ValueError(
            f"media_context must be a list of strings or None, got {type(v).__name__}."
        )

    @model_validator(mode="after")
    def check_sentence_and_context(self) -> Rapid:
        if isinstance(self.sentence, str) and isinstance(self.context, str):
            raise ValueError(
                "Both 'sentence' and 'context' cannot be strings at the same time."
            )
        return self
