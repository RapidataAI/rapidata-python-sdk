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
from rapidata.api_client.models.example_transcription_word import ExampleTranscriptionWord
from rapidata.api_client.models.i_example_payload_compare_example_payload import (
    IExamplePayloadCompareExamplePayload,
)
from rapidata.api_client.models.i_example_truth_compare_example_truth import (
    IExampleTruthCompareExampleTruth,
)
from rapidata.api_client.models.i_example_payload_line_example_payload import (
    IExamplePayloadLineExamplePayload,
)
from rapidata.api_client.models.i_example_truth_line_example_truth import (
    IExampleTruthLineExampleTruth,
)
from rapidata.api_client.models.i_example_payload_locate_example_payload import (
    IExamplePayloadLocateExamplePayload,
)
from rapidata.api_client.models.i_example_truth_locate_example_truth import (
    IExampleTruthLocateExampleTruth,
)
from rapidata.api_client.models.i_example_payload_transcription_example_payload import (
    IExamplePayloadTranscriptionExamplePayload,
)
from rapidata.api_client.models.i_example_truth_transcription_example_truth import (
    IExampleTruthTranscriptionExampleTruth,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.i_example_payload import IExamplePayload
from rapidata.api_client.models.i_example_truth import IExampleTruth
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._asset_mapper import AssetMapper
from rapidata.rapidata_client.validation.rapids.box import Box, calculate_boxes_coverage


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

    def add_locate_example(
        self,
        instruction: str,
        truth: list[Box],
        datapoint: str,
        required_precision: float | None = None,
        required_completeness: float | None = None,
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> None:
        """Add a locate example to the audience.

        Args:
            instruction (str): Instruction shown to the labeler — what to locate.
            truth (list[Box]): The bounding boxes that mark the correct regions.
                The labeler's coordinate must fall inside at least one box.
            datapoint (str): The image (URL or path) to use as the example.
            required_precision (float, optional): Minimum fraction of the
                labeler's coordinates that must fall inside the boxes. Defaults
                to None (uses the platform's default).
            required_completeness (float, optional): Minimum fraction of boxes
                that must each contain at least one labeler coordinate. Defaults
                to None.
            context (str, optional): Extra text shown to the labeler. Defaults to None.
            media_context (str, optional): Extra media (URL/path) shown alongside the
                instruction. Defaults to None.
            explanation (str, optional): Shown if the labeler answers wrong. Defaults to None.
            settings (Sequence[RapidataSetting], optional): Settings applied as feature
                flags on the example. Defaults to None.
        """
        from rapidata.api_client.models.add_example_to_audience_endpoint_input import (
            AddExampleToAudienceEndpointInput,
        )

        if not truth:
            raise ValueError("Locate example requires at least one box in truth")

        uploaded_name = self._asset_uploader.upload_asset(datapoint)
        asset_input = self._asset_mapper.create_existing_asset_input(uploaded_name)

        payload = IExamplePayload(
            actual_instance=IExamplePayloadLocateExamplePayload(
                _t="LocateExamplePayload", target=instruction
            )
        )
        model_truth = IExampleTruth(
            actual_instance=IExampleTruthLocateExampleTruth(
                _t="LocateExampleTruth",
                boundingBoxes=[box.to_model() for box in truth],
                requiredPrecision=required_precision,
                requiredCompleteness=required_completeness,
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
                randomCorrectProbability=calculate_boxes_coverage(truth),
                featureFlags=[s._to_feature_flag() for s in settings] if settings else None,
            ),
        )

    def add_line_example(
        self,
        instruction: str,
        datapoint: str,
        truth: list[Box] | None = None,
        required_precision: float | None = None,
        required_completeness: float | None = None,
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> None:
        """Add a line (draw-a-line) example to the audience.

        Args:
            instruction (str): Instruction shown to the labeler — what to draw a line through.
            datapoint (str): The image (URL or path) to use as the example.
            truth (list[Box], optional): Optional bounding boxes the line must pass through.
                When omitted (or empty), line examples are scored by annotator consensus
                rather than against a ground truth. When provided, line points are graded
                against the union of the boxes (precision + completeness, same as Locate).
                Defaults to None.
            required_precision (float, optional): Minimum fraction of line points that must
                fall inside the boxes. Ignored when ``truth`` is omitted. Defaults to None.
            required_completeness (float, optional): Minimum fraction of boxes that must
                each contain at least one line point. Ignored when ``truth`` is omitted.
                Defaults to None.
            context (str, optional): Extra text shown to the labeler. Defaults to None.
            media_context (str, optional): Extra media (URL/path) shown alongside the
                instruction. Defaults to None.
            explanation (str, optional): Shown if the labeler answers wrong. Defaults to None.
            settings (Sequence[RapidataSetting], optional): Settings applied as feature
                flags on the example. Defaults to None.
        """
        from rapidata.api_client.models.add_example_to_audience_endpoint_input import (
            AddExampleToAudienceEndpointInput,
        )

        uploaded_name = self._asset_uploader.upload_asset(datapoint)
        asset_input = self._asset_mapper.create_existing_asset_input(uploaded_name)

        payload = IExamplePayload(
            actual_instance=IExamplePayloadLineExamplePayload(
                _t="LineExamplePayload", target=instruction
            )
        )

        # Narrow `truth` once so pyright sees `boxes` as list[Box] below.
        boxes: list[Box] = truth if truth else []
        has_boxes = len(boxes) > 0
        model_truth = IExampleTruth(
            actual_instance=IExampleTruthLineExampleTruth(
                _t="LineExampleTruth",
                boundingBoxes=[box.to_model() for box in boxes] if has_boxes else None,
                requiredPrecision=required_precision if has_boxes else None,
                requiredCompleteness=required_completeness if has_boxes else None,
            )
        )

        # When boxes are provided, use the union-area as the random baseline
        # (matches Locate). When none, line examples have no scorable ground
        # truth — pick a small but non-zero number so the example still has
        # recruiting weight (matches the dashboard form).
        random_correct_probability = (
            calculate_boxes_coverage(boxes) if has_boxes else 0.1
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
                randomCorrectProbability=random_correct_probability,
                featureFlags=[s._to_feature_flag() for s in settings] if settings else None,
            ),
        )

    def add_transcription_example(
        self,
        instruction: str,
        sentence: str,
        truth: list[int],
        datapoint: str,
        required_precision: float | None = None,
        required_completeness: float | None = None,
        strict_grading: bool | None = None,
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
        settings: Sequence[RapidataSetting] | None = None,
    ) -> None:
        """Add a transcription (select-correct-words) example to the audience.

        Args:
            instruction (str): Instruction shown to the labeler.
            sentence (str): The full transcription, split into words on whitespace.
                Each whitespace-separated token becomes one selectable word.
            truth (list[int]): Indices of the words (0-based, in the order they
                appear in ``sentence``) that must be selected for a correct answer.
            datapoint (str): The audio asset (URL or path) being transcribed.
            required_precision (float, optional): Minimum fraction of selected words
                that must be correct. Defaults to None.
            required_completeness (float, optional): Minimum fraction of correct words
                that must be selected. Defaults to None.
            strict_grading (bool, optional): When True, missing required words are
                penalised more harshly. Defaults to None.
            context (str, optional): Extra text shown to the labeler. Defaults to None.
            media_context (str, optional): Extra media (URL/path) shown alongside the
                instruction. Defaults to None.
            explanation (str, optional): Shown if the labeler answers wrong. Defaults to None.
            settings (Sequence[RapidataSetting], optional): Settings applied as feature
                flags on the example. Defaults to None.
        """
        from rapidata.api_client.models.add_example_to_audience_endpoint_input import (
            AddExampleToAudienceEndpointInput,
        )

        words = sentence.split(" ")
        if not words:
            raise ValueError("Transcription example requires a non-empty sentence")
        if not truth:
            raise ValueError("Transcription example requires at least one truth index")
        for index in truth:
            if index < 0 or index >= len(words):
                raise ValueError(
                    f"Truth index {index} is out of range for sentence with "
                    f"{len(words)} words"
                )

        transcription_words = [
            ExampleTranscriptionWord(word=word, wordIndex=i)
            for i, word in enumerate(words)
        ]
        correct_words = [
            ExampleTranscriptionWord(word=words[i], wordIndex=i) for i in truth
        ]

        uploaded_name = self._asset_uploader.upload_asset(datapoint)
        asset_input = self._asset_mapper.create_existing_asset_input(uploaded_name)

        payload = IExamplePayload(
            actual_instance=IExamplePayloadTranscriptionExamplePayload(
                _t="TranscriptionExamplePayload",
                title=instruction,
                transcription=transcription_words,
            )
        )
        model_truth = IExampleTruth(
            actual_instance=IExampleTruthTranscriptionExampleTruth(
                _t="TranscriptionExampleTruth",
                correctWords=correct_words,
                strictGrading=strict_grading,
                requiredPrecision=required_precision,
                requiredCompleteness=required_completeness,
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
                randomCorrectProbability=len(correct_words) / len(transcription_words),
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
