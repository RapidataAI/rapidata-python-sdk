from typing import Literal
from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.rapidata_client.settings import RapidataSetting
from typing import Sequence
from rapidata.api_client.models.classify_payload import (
    ClassifyPayload,
    ClassifyPayloadCategory,
)
from rapidata.api_client.models.attach_category_truth import AttachCategoryTruth


class ClassifyRapid(Rapid):
    def __init__(
        self,
        instruction: str,
        answer_options: list[str],
        datapoint: str,
        truths: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ):
        super().__init__(
            asset=datapoint,
            data_type=data_type,
            context=context,
            media_context=media_context,
            explanation=explanation,
            payload=ClassifyPayload(
                _t="ClassifyPayload",
                categories=[
                    ClassifyPayloadCategory(label=option, value=option)
                    for option in answer_options
                ],
                title=instruction,
            ),
            truth=AttachCategoryTruth(
                correctCategories=truths, _t="AttachCategoryTruth"
            ),
            random_correct_probability=len(truths) / len(answer_options),
            settings=settings,
        )
