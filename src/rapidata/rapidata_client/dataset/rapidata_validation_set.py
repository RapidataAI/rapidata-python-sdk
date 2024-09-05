import os
from typing import Any
from rapidata.api_client.models.add_validation_rapid_model import (
    AddValidationRapidModel,
)
from rapidata.api_client.models.add_validation_rapid_model_payload import (
    AddValidationRapidModelPayload,
)
from rapidata.api_client.models.add_validation_rapid_model_truth import (
    AddValidationRapidModelTruth,
)
from rapidata.api_client.models.attach_category_truth import AttachCategoryTruth
from rapidata.api_client.models.bounding_box_payload import BoundingBoxPayload
from rapidata.api_client.models.bounding_box_truth import BoundingBoxTruth
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.api_client.models.compare_payload import ComparePayload
from rapidata.api_client.models.compare_truth import CompareTruth
from rapidata.api_client.models.datapoint_metadata_model_metadata_inner import (
    DatapointMetadataModelMetadataInner,
)
from rapidata.api_client.models.empty_validation_truth import EmptyValidationTruth
from rapidata.api_client.models.free_text_payload import FreeTextPayload
from rapidata.api_client.models.line_payload import LinePayload
from rapidata.api_client.models.line_truth import LineTruth
from rapidata.api_client.models.locate_box_truth import LocateBoxTruth
from rapidata.api_client.models.locate_payload import LocatePayload
from rapidata.api_client.models.named_entity_payload import NamedEntityPayload
from rapidata.api_client.models.named_entity_truth import NamedEntityTruth
from rapidata.api_client.models.polygon_payload import PolygonPayload
from rapidata.api_client.models.polygon_truth import PolygonTruth
from rapidata.api_client.models.transcription_payload import TranscriptionPayload
from rapidata.api_client.models.transcription_truth import TranscriptionTruth
from rapidata.api_client.models.transcription_word import TranscriptionWord
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.service.openapi_service import OpenAPIService


class RapidataValidationSet:
    """A class for interacting with a Rapidata validation set.

    Get a `ValidationSet` either by using `rapi.get_validation_set(id)` to get an exisitng validation set or by using `rapi.new_validation_set(name)` to create a new validation set.
    """

    def __init__(self, validation_set_id, openapi_service: OpenAPIService):
        self.id = validation_set_id
        self.openapi_service = openapi_service

    def add_general_validation_rapid(
        self,
        payload: (
            BoundingBoxPayload
            | ClassifyPayload
            | ComparePayload
            | FreeTextPayload
            | LinePayload
            | LocatePayload
            | NamedEntityPayload
            | PolygonPayload
            | TranscriptionPayload
        ),
        truths: (
            AttachCategoryTruth
            | BoundingBoxTruth
            | CompareTruth
            | EmptyValidationTruth
            | LineTruth
            | LocateBoxTruth
            | NamedEntityTruth
            | PolygonTruth
            | TranscriptionTruth
        ),
        metadata: list[Metadata],
        media_paths: str | list[str],
        randomCorrectProbability: float,
    ) -> None:
        """Add a validation rapid to the validation set.

        Args:
            payload (Union[BoundingBoxPayload, ClassifyPayload, ComparePayload, FreeTextPayload, LinePayload, LocatePayload, NamedEntityPayload, PolygonPayload, TranscriptionPayload]): The payload for the rapid.
            truths (Union[AttachCategoryTruth, BoundingBoxTruth, CompareTruth, EmptyValidationTruth, LineTruth, LocateBoxTruth, NamedEntityTruth, PolygonTruth, TranscriptionTruth]): The truths for the rapid.
            metadata (list[Metadata]): The metadata for the rapid.
            media_paths (Union[str, list[str]]): The media paths for the rapid.
            randomCorrectProbability (float): The random correct probability for the rapid.

        Returns:
            None
        """
        model = AddValidationRapidModel(
            validationSetId=self.id,
            payload=AddValidationRapidModelPayload(payload),
            truth=AddValidationRapidModelTruth(truths),
            metadata=[
                DatapointMetadataModelMetadataInner(meta.to_model())
                for meta in metadata
            ],
            randomCorrectProbability=randomCorrectProbability,
        )

        self.openapi_service.validation_api.validation_add_validation_rapid_post(
            model=model, files=media_paths if isinstance(media_paths, list) else [media_paths]  # type: ignore
        )

    def add_classify_validation_rapid(
        self,
        media_path: str,
        question: str,
        categories: list[str],
        truths: list[str],
        metadata: list[Metadata] = [],
    ) -> None:
        """Add a classify rapid to the validation set.

        Args:
            media_path (str): The path to the media file.
            question (str): The question for the rapid.
            categories (list[str]): The list of categories for the rapid.
            truths (list[str]): The list of truths for the rapid.
            metadata (list[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            None
        """
        payload = ClassifyPayload(
            _t="ClassifyPayload", possibleCategories=categories, title=question
        )
        model_truth = AttachCategoryTruth(
            correctCategories=truths, _t="AttachCategoryTruth"
        )

        self.add_general_validation_rapid(
            payload=payload,
            truths=model_truth,
            metadata=metadata,
            media_paths=media_path,
            randomCorrectProbability=len(truths) / len(categories),
        )

    def add_compare_validation_rapid(
        self,
        media_paths: list[str],
        question: str,
        truth: str,
        metadata: list[Metadata] = [],
    ) -> None:
        """Add a compare rapid to the validation set.

        Args:
            media_paths (list[str]): The list of media paths for the rapid.
            question (str): The question for the rapid.
            truth (str): The path to the truth file.
            metadata (list[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            None

        Raises:
            ValueError: If the number of media paths is not exactly two.
            FileNotFoundError: If any of the specified files are not found.
        """
        payload = ComparePayload(_t="ComparePayload", criteria=question)
        # take only last part of truth path
        truth = os.path.basename(truth)
        model_truth = CompareTruth(_t="CompareTruth", winnerId=truth)

        if len(media_paths) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        # check that files exist
        for media_path in media_paths:
            if not os.path.exists(media_path):
                raise FileNotFoundError(f"File not found: {media_path}")

        self.add_general_validation_rapid(
            payload=payload,
            truths=model_truth,
            metadata=metadata,
            media_paths=media_paths,
            randomCorrectProbability=1 / len(media_paths),
        )

    def add_transcription_validation_rapid(
        self,
        media_path: str,
        question: str,
        transcription: list[str],
        correct_words: list[str],
        strict_grading: bool | None = None,
        metadata: list[Metadata] = [],
    ) -> None:
        """Add a transcription rapid to the validation set.

        Args:
            media_path (str): The path to the media file.
            question (str): The question for the rapid.
            transcription (list[str]): The transcription for the rapid.
            correct_words (list[str]): The list of correct words for the rapid.
            strict_grading (Optional[bool], optional): The strict grading for the rapid. Defaults to None.
            metadata (list[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            None

        Raises:
            ValueError: If a correct word is not found in the transcription.
        """
        transcription_words = [
            TranscriptionWord(word=word, wordIndex=i)
            for i, word in enumerate(transcription)
        ]

        correct_transcription_words = []
        for word in correct_words:
            if word not in transcription:
                raise ValueError(f"Correct word '{word}' not found in transcription")
            correct_transcription_words.append(
                TranscriptionWord(word=word, wordIndex=transcription.index(word))
            )

        payload = TranscriptionPayload(
            _t="TranscriptionPayload", title=question, transcription=transcription_words
        )

        model_truth = TranscriptionTruth(
            _t="TranscriptionTruth",
            correctWords=correct_transcription_words,
            strictGrading=strict_grading,
        )

        self.add_general_validation_rapid(
            payload=payload,
            truths=model_truth,
            metadata=metadata,
            media_paths=media_path,
            randomCorrectProbability=len(correct_words) / len(transcription),
        )
