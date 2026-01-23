from typing import Literal

from rapidata.api_client.models.i_validation_truth_attach_category_truth import (
    IValidationTruthAttachCategoryTruth,
)
from rapidata.api_client.models.i_rapid_payload_classify_payload import (
    IRapidPayloadClassifyPayload,
)
from rapidata.api_client.models.classify_payload_category import ClassifyPayloadCategory
from rapidata.api_client.models.i_rapid_payload_compare_payload import (
    IRapidPayloadComparePayload,
)
from rapidata.api_client.models.i_validation_truth_compare_truth import (
    IValidationTruthCompareTruth,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_validation_truth import IValidationTruth
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._asset_mapper import AssetMapper


class AudienceExampleHandler:
    """
    Can be used to build different types of examples. That can then be added to Example sets
    """

    def __init__(self, openapi_service: OpenAPIService, audience_id: str):
        self._openapi_service = openapi_service
        self._audience_id = audience_id
        self._asset_uploader = AssetUploader(openapi_service)
        self._asset_mapper = AssetMapper()

    def add_classification_example(
        self,
        instruction: str,
        answer_options: list[str],
        datapoint: str,
        truth: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> None:
        """add a classification example to the audience

        Args:
            instruction (str): The instruction/question to be shown to the labeler.
            answer_options (list[str]): The options that the labeler can choose from to answer the question.
            datapoint (str): The datapoint that the labeler will be labeling.
            truth (list[str]): The correct answers to the question.
            data_type (str, optional): The type of the datapoint. Defaults to "media" (any form of image, video or audio).
            context (str, optional): The context is text that will be shown in addition to the instruction. Defaults to None.
            media_context (str, optional): The media context is a link to an image / video that will be shown in addition to the instruction (can be combined with context). Defaults to None.
            explanation (str, optional): The explanation that will be shown to the labeler if the answer is wrong. Defaults to None.
        """
        from rapidata.api_client.models.add_rapid_to_audience_model import (
            AddRapidToAudienceModel,
        )

        if not isinstance(truth, list):
            raise ValueError("Truth must be a list of strings")

        if not all(truth in answer_options for truth in truth):
            raise ValueError("Truth must be part of the answer options")

        if data_type == "media":
            uploaded_name = self._asset_uploader.upload_asset(datapoint)
            asset_input = self._asset_mapper.create_existing_asset_input(uploaded_name)
        else:
            asset_input = self._asset_mapper.create_text_input(datapoint)

        payload = IRapidPayload(
            actual_instance=IRapidPayloadClassifyPayload(
                _t="ClassifyPayload",
                categories=[
                    ClassifyPayloadCategory(label=option, value=option)
                    for option in answer_options
                ],
                title=instruction,
            )
        )
        model_truth = IValidationTruth(
            actual_instance=IValidationTruthAttachCategoryTruth(
                correctCategories=truth, _t="AttachCategoryTruth"
            )
        )

        self._openapi_service.audience_api.audience_audience_id_rapid_post(
            audience_id=self._audience_id,
            add_rapid_to_audience_model=AddRapidToAudienceModel(
                asset=asset_input,
                payload=payload,
                truth=model_truth,
                context=context,
                contextAsset=(
                    self._asset_mapper.create_existing_asset_input(
                        self._asset_uploader.upload_asset(media_context)
                    )
                    if media_context
                    else None
                ),
                explanation=explanation,
                randomCorrectProbability=len(truth) / len(answer_options),
            ),
        )

    def add_compare_example(
        self,
        instruction: str,
        truth: str,
        datapoint: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> None:
        """add a compare example to the audience

        Args:
            instruction (str): The instruction that the labeler will be comparing the assets on.
            truth (str): The correct answer to the comparison. (has to be one of the assets)
            datapoint (list[str]): The two assets that the labeler will be comparing.
            data_type (str, optional): The type of the datapoint. Defaults to "media" (any form of image, video or audio).
            context (str, optional): The context is text that will be shown in addition to the instruction. Defaults to None.
            media_context (str, optional): The media context is a link to an image / video that will be shown in addition to the instruction (can be combined with context). Defaults to None.
            explanation (str, optional): The explanation that will be shown to the labeler if the answer is wrong. Defaults to None.
        """
        from rapidata.api_client.models.add_rapid_to_audience_model import (
            AddRapidToAudienceModel,
        )

        payload = IRapidPayload(
            actual_instance=IRapidPayloadComparePayload(
                _t="ComparePayload", criteria=instruction
            )
        )

        uploaded_names: list[str] = []
        if data_type == "media":
            uploaded_names = [self._asset_uploader.upload_asset(dp) for dp in datapoint]
            asset_input = self._asset_mapper.create_existing_asset_input(uploaded_names)
        else:
            asset_input = self._asset_mapper.create_text_input(datapoint)

        if truth not in datapoint:
            raise ValueError("Truth must be one of the datapoints")

        truth_index = datapoint.index(truth)
        if data_type == "media":
            winner_id = uploaded_names[truth_index]
        else:
            winner_id = truth
        model_truth = IValidationTruth(
            actual_instance=IValidationTruthCompareTruth(
                _t="CompareTruth", winnerId=winner_id
            )
        )

        if len(datapoint) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        self._openapi_service.audience_api.audience_audience_id_rapid_post(
            audience_id=self._audience_id,
            add_rapid_to_audience_model=AddRapidToAudienceModel(
                asset=asset_input,
                payload=payload,
                truth=model_truth,
                context=context,
                contextAsset=(
                    self._asset_mapper.create_existing_asset_input(
                        self._asset_uploader.upload_asset(media_context)
                    )
                    if media_context
                    else None
                ),
                explanation=explanation,
                randomCorrectProbability=0.5,
            ),
        )

    def __str__(self) -> str:
        return "RapidsManager"

    def __repr__(self) -> str:
        return self.__str__()
