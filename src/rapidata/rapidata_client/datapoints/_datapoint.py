from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, model_validator, field_validator
from typing_extensions import Self
from rapidata.rapidata_client.datapoints.assets.constants import (
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_AUDIO_EXTENSIONS,
)
from rapidata.rapidata_client.config import logger

if TYPE_CHECKING:
    from rapidata.api_client.models.asset_type import AssetType
    from rapidata.api_client.models.prompt_type import PromptType


def coerce_media_context(value: object) -> list[str] | None:
    """Normalize a ``media_context`` value to ``list[str] | None``.

    Accepts ``str`` for backward compatibility — emits a deprecation warning
    and wraps it in a single-element list so the rest of the SDK only ever
    has to deal with ``list[str]``. This is the single source of truth for
    media_context coercion; both the ``Datapoint`` and ``Rapid`` field
    validators delegate to it, as do the audience public APIs.
    """
    if value is None:
        return None
    if isinstance(value, str):
        if value == "":
            raise ValueError(
                "media_context cannot be an empty string. If not needed, set to None."
            )
        logger.warning(
            "Passing a string for media_context is deprecated; pass a list of strings instead. "
            "Wrapping the value in a single-element list."
        )
        return [value]
    if isinstance(value, list):
        if len(value) == 0:
            raise ValueError(
                "media_context cannot be an empty list. If not needed, set to None."
            )
        if any(not isinstance(item, str) or item == "" for item in value):
            raise ValueError(
                "Every entry in a media_context list must be a non-empty string."
            )
        return value
    raise ValueError(
        f"media_context must be a list of strings or None, got {type(value).__name__}."
    )


class Datapoint(BaseModel):
    asset: str | list[str]
    data_type: Literal["text", "media"]
    context: str | None = None
    media_context: list[str] | None = None
    sentence: str | None = None
    private_metadata: dict[str, str] | None = None
    group: str | None = None

    @field_validator("context")
    @classmethod
    def context_not_empty(cls, v: str | None) -> str | None:
        if v is not None and v == "":
            raise ValueError(
                "context cannot be an empty string. If not needed, set to None."
            )
        return v

    @field_validator("media_context", mode="before")
    @classmethod
    def media_context_normalize(cls, v: object) -> list[str] | None:
        return coerce_media_context(v)

    @field_validator("sentence")
    @classmethod
    def sentence_has_space(cls, v: str | None) -> str | None:
        if v is not None and len(v.split()) <= 1:
            raise ValueError("sentence must contain at least two words.")
        return v

    @model_validator(mode="after")
    def check_sentence_and_context(self) -> Self:
        if isinstance(self.sentence, str) and isinstance(self.context, str):
            raise ValueError(
                "Both 'sentence' and 'context' cannot be strings at the same time."
            )
        return self

    def get_asset_type(self) -> AssetType:
        from rapidata.api_client.models.asset_type import AssetType
        from urllib.parse import urlparse

        if self.data_type == "text":
            return AssetType.TEXT

        evaluation_asset = self.asset[0] if isinstance(self.asset, list) else self.asset

        # Compare extensions case-insensitively and ignore URL query /
        # fragment so `photo.JPG` and `https://x/image.png?v=2` are both
        # recognised correctly.
        parsed_path = urlparse(evaluation_asset).path or evaluation_asset
        lower = parsed_path.lower()

        if any(lower.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
            return AssetType.IMAGE
        elif any(lower.endswith(ext) for ext in ALLOWED_VIDEO_EXTENSIONS):
            return AssetType.VIDEO
        elif any(lower.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS):
            return AssetType.AUDIO
        else:
            logger.debug(
                f"Cannot get asset type for asset type: {type(evaluation_asset)}"
            )
            return AssetType.NONE

    def get_prompt_type(self) -> list[PromptType]:
        from rapidata.api_client.models.prompt_type import PromptType

        prompt_types = []
        if self.context:
            prompt_types.append(PromptType.TEXT)
        if self.media_context:
            prompt_types.append(PromptType.ASSET)

        if len(prompt_types) == 0:
            return [PromptType.NONE]

        return prompt_types
