from dataclasses import dataclass
import os
from typing import Any, Union
from rapidata.api_client.models.add_validation_rapid_model import AddValidationRapidModel
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
from rapidata.service.openapi_service import OpenAPIService


@dataclass
class ValidatioRapidParts:
    question: str
    media_paths: str | list[str]
    payload: Union[
        BoundingBoxPayload,
        ClassifyPayload,
        ComparePayload,
        FreeTextPayload,
        LinePayload,
        LocatePayload,
        NamedEntityPayload,
        PolygonPayload,
        TranscriptionPayload,
    ]
    truths: Union[
        AttachCategoryTruth,
        BoundingBoxTruth,
        CompareTruth,
        EmptyValidationTruth,
        LineTruth,
        LocateBoxTruth,
        NamedEntityTruth,
        PolygonTruth,
        TranscriptionTruth,
    ]
    metadata: Any
    randomCorrectProbability: float


class ValidationSetBuilder:

    def __init__(self, name: str, openapi_service: OpenAPIService):
        self.name = name
        self.openapi_service = openapi_service
        self.validation_set_id: str | None = None
        self._rapid_parts: list[ValidatioRapidParts] = []

    def create(self):
        result = (
            self.openapi_service.validation_api.validation_create_validation_set_post(
                name=self.name
            )
        )
        self.validation_set_id = result.validation_set_id

        if self.validation_set_id is None:
            raise ValueError("Failed to create validation set")

        for rapid_part in self._rapid_parts:
            model = AddValidationRapidModel(
                validationSetId=self.validation_set_id,
                payload=AddValidationRapidModelPayload(rapid_part.payload),
                truth=AddValidationRapidModelTruth(rapid_part.truths),
                metadata=rapid_part.metadata or [],
                randomCorrectProbability=rapid_part.randomCorrectProbability,
            )

            self.openapi_service.validation_api.validation_add_validation_rapid_post(
                model=model, files=rapid_part.media_paths if isinstance(rapid_part.media_paths, list) else [rapid_part.media_paths]  # type: ignore
            )

        return str(self.validation_set_id)

    def add_classify_rapid(
        self, media_path: str, question: str, categories: list[str], truths: list[str]
    ):
        payload = ClassifyPayload(
            _t="ClassifyPaylod", possibleCategories=categories, title=question
        )
        model_truth = AttachCategoryTruth(
            correctCategories=truths, _t="AttachCategoryTruth"
        )

        self._rapid_parts.append(
            ValidatioRapidParts(
                question=question,
                media_paths=media_path,
                payload=payload,
                truths=model_truth,
                metadata=None,
                randomCorrectProbability=len(truths) / len(categories),
            )
        )

        return self

    def add_compare_rapid(self, media_paths: list[str], question: str, truth: str):
        payload = ComparePayload(_t="ComparePayload", criteria=question)
        model_truth = CompareTruth(_t="CompareTruth", winnerId=truth)

        if len(media_paths) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        # check that files exist
        for media_path in media_paths:
            if not os.path.exists(media_path):
                raise FileNotFoundError(f"File not found: {media_path}")
            
        # take only last part of truth path
        truth = os.path.basename(truth)

        self._rapid_parts.append(
            ValidatioRapidParts(
                question=question,
                media_paths=media_paths,
                payload=payload,
                truths=model_truth,
                metadata=None,
                randomCorrectProbability=1 / len(media_paths),
            )
        )

        return self

    def add_transcription_rapid(
        self,
        media_path: str,
        question: str,
        transcription: list[str],
        correct_words: list[str],
        strict_grading: bool | None = None,
    ):
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

        self._rapid_parts.append(
            ValidatioRapidParts(
                question=question,
                media_paths=media_path,
                payload=payload,
                truths=model_truth,
                metadata=None,
                randomCorrectProbability=1 / len(transcription),
            )
        )

        return self
