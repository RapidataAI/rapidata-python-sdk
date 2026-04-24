from __future__ import annotations

from typing import Literal, TYPE_CHECKING, Any, Sequence, cast

if TYPE_CHECKING:
    from rapidata.rapidata_client.validation.rapids.rapids import Rapid
    from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting

from rapidata.api_client.models.i_example_truth_classify_example_truth import (
    IExampleTruthClassifyExampleTruth,
)
from rapidata.api_client.models.i_example_payload_classify_example_payload import (
    IExamplePayloadClassifyExamplePayload,
)
from rapidata.api_client.models.example_category import ExampleCategory
from rapidata.api_client.models.i_example_payload_compare_example_payload import (
    IExamplePayloadCompareExamplePayload,
)
from rapidata.api_client.models.i_example_truth_compare_example_truth import (
    IExampleTruthCompareExampleTruth,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.i_example_payload import IExamplePayload
from rapidata.api_client.models.i_example_truth import IExampleTruth
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
        settings: Sequence[RapidataSetting] | None = None,
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
            settings (Sequence[RapidataSetting], optional): The list of settings to apply to the example as feature flags. Controls how the example is rendered to the labeler (e.g. ``NoShuffleSetting`` to keep the order of answer options). Defaults to None.
        """
        from rapidata.api_client.models.add_example_to_audience_endpoint_input import (
            AddExampleToAudienceEndpointInput,
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

        payload = IExamplePayload(
            actual_instance=IExamplePayloadClassifyExamplePayload(
                _t="ClassifyExamplePayload",
                categories=[
                    ExampleCategory(label=option, value=option)
                    for option in answer_options
                ],
                title=instruction,
            )
        )
        model_truth = IExampleTruth(
            actual_instance=IExampleTruthClassifyExampleTruth(
                correctCategories=truth, _t="ClassifyExampleTruth"
            )
        )

        self._openapi_service.audience.examples_api.audience_audience_id_example_post(
            audience_id=self._audience_id,
            add_example_to_audience_endpoint_input=AddExampleToAudienceEndpointInput(
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
                featureFlags=[s._to_feature_flag() for s in settings] if settings else None,
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
        settings: Sequence[RapidataSetting] | None = None,
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
            settings (Sequence[RapidataSetting], optional): The list of settings to apply to the example as feature flags. Controls how the example is rendered to the labeler (e.g. ``ComparePanoramaSetting`` to render panoramic images). Defaults to None.
        """
        from rapidata.api_client.models.add_example_to_audience_endpoint_input import (
            AddExampleToAudienceEndpointInput,
        )

        payload = IExamplePayload(
            actual_instance=IExamplePayloadCompareExamplePayload(
                _t="CompareExamplePayload", criteria=instruction
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
        model_truth = IExampleTruth(
            actual_instance=IExampleTruthCompareExampleTruth(
                _t="CompareExampleTruth", winnerId=winner_id
            )
        )

        if len(datapoint) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        self._openapi_service.audience.examples_api.audience_audience_id_example_post(
            audience_id=self._audience_id,
            add_example_to_audience_endpoint_input=AddExampleToAudienceEndpointInput(
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
                featureFlags=[s._to_feature_flag() for s in settings] if settings else None,
            ),
        )

    def _add_rapid_example(self, rapid: Rapid) -> None:
        """Add a rapid example to the audience (private method).

        Args:
            rapid (Rapid): The rapid object to add as an example.
        """
        from rapidata.api_client.models.add_example_to_audience_endpoint_input import (
            AddExampleToAudienceEndpointInput,
        )

        # Handle asset uploading based on data type
        if rapid.data_type == "media":
            if isinstance(rapid.asset, list):
                uploaded_names = [
                    self._asset_uploader.upload_asset(asset) for asset in rapid.asset
                ]
                asset_input = self._asset_mapper.create_existing_asset_input(
                    uploaded_names
                )
            else:
                uploaded_name = self._asset_uploader.upload_asset(rapid.asset)
                asset_input = self._asset_mapper.create_existing_asset_input(
                    uploaded_name
                )
        else:
            asset_input = self._asset_mapper.create_text_input(rapid.asset)

        # Handle media context if present
        context_asset = None
        if rapid.media_context:
            context_asset = self._asset_mapper.create_existing_asset_input(
                self._asset_uploader.upload_asset(rapid.media_context)
            )

        # Convert IValidationTruthModel to IExampleTruth
        # Both types are structurally identical (same JSON schema), differing only in class names
        # The dict-based conversion is safe and preserves all data
        model_truth: IExampleTruth | None = None
        if rapid.truth:
            truth_dict = cast(dict[str, Any], rapid.truth.to_dict())
            model_truth = IExampleTruth.from_dict(truth_dict)

        # Convert IRapidPayload to IExamplePayload
        payload_dict = cast(dict[str, Any], rapid.payload.to_dict())
        example_payload = IExamplePayload.from_dict(payload_dict)

        self._openapi_service.audience.examples_api.audience_audience_id_example_post(
            audience_id=self._audience_id,
            add_example_to_audience_endpoint_input=AddExampleToAudienceEndpointInput(
                asset=asset_input,
                payload=example_payload,
                truth=model_truth,
                context=rapid.context,
                contextAsset=context_asset,
                explanation=rapid.explanation,
                randomCorrectProbability=rapid.random_correct_probability or 0.5,
                featureFlags=(
                    [s._to_feature_flag() for s in rapid.settings]
                    if rapid.settings
                    else None
                ),
            ),
        )

    def __str__(self) -> str:
        return "RapidsManager"

    def __repr__(self) -> str:
        return self.__str__()
