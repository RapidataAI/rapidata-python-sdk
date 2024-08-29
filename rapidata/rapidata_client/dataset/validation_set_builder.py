import os
from rapidata.api_client.models.attach_category_truth import AttachCategoryTruth
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.api_client.models.compare_payload import ComparePayload
from rapidata.api_client.models.compare_truth import CompareTruth
from rapidata.api_client.models.transcription_payload import TranscriptionPayload
from rapidata.api_client.models.transcription_truth import TranscriptionTruth
from rapidata.api_client.models.transcription_word import TranscriptionWord
from rapidata.rapidata_client.dataset.rapidata_validation_set import (
    RapidataValidationSet,
)
from rapidata.rapidata_client.dataset.validation_rapid_parts import ValidatioRapidParts
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.service.openapi_service import OpenAPIService


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

        validation_set = RapidataValidationSet(
            validation_set_id=self.validation_set_id,
            openapi_service=self.openapi_service,
        )

        for rapid_part in self._rapid_parts:
            validation_set.add_validation_rapid(
                payload=rapid_part.payload,
                truths=rapid_part.truths,
                metadata=rapid_part.metadata,
                media_paths=rapid_part.media_paths,
                randomCorrectProbability=rapid_part.randomCorrectProbability,
            )

        return validation_set

    def add_classify_rapid(
        self,
        media_path: str,
        question: str,
        categories: list[str],
        truths: list[str],
        metadata: list[Metadata] = [],
    ):
        payload = ClassifyPayload(
            _t="ClassifyPayload", possibleCategories=categories, title=question
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
                metadata=metadata,
                randomCorrectProbability=len(truths) / len(categories),
            )
        )

        return self

    def add_compare_rapid(
        self,
        media_paths: list[str],
        question: str,
        truth: str,
        metadata: list[Metadata] = [],
    ):
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

        self._rapid_parts.append(
            ValidatioRapidParts(
                question=question,
                media_paths=media_paths,
                payload=payload,
                truths=model_truth,
                metadata=metadata,
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
        metadata: list[Metadata] = [],
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
                metadata=metadata,
                randomCorrectProbability=1 / len(transcription),
            )
        )

        return self
