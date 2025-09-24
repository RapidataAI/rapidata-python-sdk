from typing import Literal

from pydantic import BaseModel, model_validator
from typing_extensions import Self


class Datapoint(BaseModel):
    assets: str | list[str]
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
