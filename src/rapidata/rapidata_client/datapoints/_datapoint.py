from typing import Literal

from pydantic import BaseModel, model_validator
from typing_extensions import Self
from rapidata.rapidata_client.datapoints.assets.constants import (
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_AUDIO_EXTENSIONS,
)
from rapidata.api_client.models.asset_type import AssetType
from rapidata.api_client.models.prompt_type import PromptType
from rapidata.rapidata_client.config import logger


class Datapoint(BaseModel):
    asset: str | list[str]
    data_type: Literal["text", "media"]
    context: str | None = None
    media_context: str | None = None
    sentence: str | None = None
    private_note: str | None = None

    @model_validator(mode="after")
    def check_sentence_and_context(self) -> Self:
        if isinstance(self.sentence, str) and isinstance(self.context, str):
            raise ValueError(
                "Both 'sentence' and 'context' cannot be strings at the same time."
            )
        return self

    def get_asset_type(self) -> AssetType:
        if self.data_type == "text":
            return AssetType.TEXT

        evaluation_asset = self.asset[0] if isinstance(self.asset, list) else self.asset
        if any(evaluation_asset.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
            return AssetType.IMAGE
        elif any(evaluation_asset.endswith(ext) for ext in ALLOWED_VIDEO_EXTENSIONS):
            return AssetType.VIDEO
        elif any(evaluation_asset.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS):
            return AssetType.AUDIO
        else:
            logger.debug(
                f"Cannot get asset type for asset type: {type(evaluation_asset)}"
            )
            return AssetType.NONE

    def get_prompt_type(self) -> list[PromptType]:
        prompt_types = []
        if self.context:
            prompt_types.append(PromptType.TEXT)
        if self.media_context:
            prompt_types.append(PromptType.ASSET)

        if len(prompt_types) == 0:
            return [PromptType.NONE]

        return prompt_types
