import os
from rapidata.api_client.models.attach_category_truth import AttachCategoryTruth
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.api_client.models.compare_payload import ComparePayload
from rapidata.api_client.models.compare_truth import CompareTruth
from rapidata.api_client.models.transcription_payload import TranscriptionPayload
from rapidata.api_client.models.transcription_truth import TranscriptionTruth
from rapidata.api_client.models.transcription_word import TranscriptionWord
from rapidata.rapidata_client.assets._media_asset import MediaAsset
from rapidata.rapidata_client.assets._multi_asset import MultiAsset
from rapidata.rapidata_client.assets._text_asset import TextAsset
from rapidata.rapidata_client.validation.rapidata_validation_set import (
    RapidataValidationSet,
)
from rapidata.rapidata_client.validation._validation_rapid_parts import ValidatioRapidParts
from rapidata.rapidata_client.metadata._base_metadata import Metadata
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.validation.rapids.rapids import (
    Rapid, 
    ClassificationRapid,
    CompareRapid,
    SelectWordsRapid
)
from typing import Sequence


class ValidationSetBuilder:
    """The ValidationSetBuilder is used to build a validation set.
    Give the validation set a name and then add classify, compare, or transcription rapid parts to it.
    Get a `ValidationSetBuilder` by calling [`rapi.new_validation_set()`](../rapidata_client.md/#rapidata.rapidata_client.rapidata_client.RapidataClient.new_validation_set).
    """

    def __init__(self, name: str, openapi_service: OpenAPIService):
        """
        Initialize the ValidationSetBuilder.

        Args:
            name (str): The name of the validation set.
            openapi_service (OpenAPIService): An instance of OpenAPIService to interact with the API.
        """
        self.name = name
        self.openapi_service = openapi_service
        self.validation_set_id: str | None = None
        self._rapid_parts: list[ValidatioRapidParts] = []

    def _submit(self, print_confirmation: bool = True) -> RapidataValidationSet:
        """Create the validation set by executing all HTTP requests. This should be the last method called on the builder.

        Returns:
            RapidataValidationSet: A RapidataValidationSet instance.

        Raises:
            ValueError: If the validation set creation fails.
        """
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
            name=self.name,
        )

        for rapid_part in self._rapid_parts:
            validation_set._add_general_validation_rapid(
                payload=rapid_part.payload,
                truths=rapid_part.truths,
                metadata=rapid_part.metadata,
                asset=rapid_part.asset,
                randomCorrectProbability=rapid_part.randomCorrectProbability,
            )

        if print_confirmation:
            print(f"Validation set '{self.name}' created with ID {self.validation_set_id}")
            
        return validation_set
    
    def _add_rapid(self, rapid: Rapid):
        """Add a rapid to the validation set.
        To create the Rapid, use the RapidataClient.rapid_builder instance.

        Args:
            rapid (Rapid): The rapid to add to the validation set.
        """
        if not isinstance(rapid, Rapid):
            raise ValueError("This method only accepts Rapid instances")
        
        if isinstance(rapid, ClassificationRapid):
            self.__add_classify_rapid(rapid.asset, rapid.question, rapid.options, rapid.truths, rapid.metadata)

        if isinstance(rapid, CompareRapid):
            self.__add_compare_rapid(rapid.asset, rapid.criteria, rapid.truth, rapid.metadata)

        if isinstance(rapid, SelectWordsRapid):
            self.__add_select_words_rapid(rapid.asset, rapid.instruction, rapid.sentence, rapid.truths, rapid.strict_grading)

        return self
    
    def __add_classify_rapid(
        self,
        asset: MediaAsset | TextAsset,
        instruction: str,
        answer_options: list[str],
        truths: list[str],
        metadata: Sequence[Metadata] = [],
    ):
        """Add a classify rapid to the validation set.

        Args:
            asset (MediaAsset | TextAsset): The asset for the rapid.
            instruction (str): The instruction for the rapid.
            answer_options (list[str]): The list of answer_options for the rapid.
            truths (list[str]): The list of truths for the rapid.
            metadata (Sequence[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            ValidationSetBuilder: The ValidationSetBuilder instance.

        Raises:
            ValueError: If the lengths of categories and truths are inconsistent.
        """
        payload = ClassifyPayload(
            _t="ClassifyPayload", possibleCategories=answer_options, title=instruction
        )
        model_truth = AttachCategoryTruth(
            correctCategories=truths, _t="AttachCategoryTruth"
        )

        self._rapid_parts.append(
            ValidatioRapidParts(
                instruction=instruction,
                payload=payload,
                truths=model_truth,
                metadata=metadata,
                randomCorrectProbability=len(truths) / len(answer_options),
                asset=asset,
            )
        )
    
    def __add_compare_rapid(
        self,
        asset: MultiAsset,
        instruction: str,
        truth: str,
        metadata: Sequence[Metadata] = [],
    ):
        """Add a compare rapid to the validation set.

        Args:
            asset (MultiAsset): The assets for the rapid.
            instruction (str): The instruction for the comparison.
            truth (str): The truth identifier for the rapid.
            metadata (Sequence[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            ValidationSetBuilder: The ValidationSetBuilder instance.

        Raises:
            ValueError: If the number of assets is not exactly two.
        """
        payload = ComparePayload(_t="ComparePayload", criteria=instruction)
        # take only last part of truth path
        truth = os.path.basename(truth)
        model_truth = CompareTruth(_t="CompareTruth", winnerId=truth)

        if len(asset) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        self._rapid_parts.append(
            ValidatioRapidParts(
                instruction=instruction,
                payload=payload,
                truths=model_truth,
                metadata=metadata,
                randomCorrectProbability=1 / len(asset),
                asset=asset,
            )
        )
    
    def __add_select_words_rapid(
        self,
        asset: MediaAsset | TextAsset,
        instruction: str,
        select_words: str,
        truths: list[int],
        strict_grading: bool | None = None,
        metadata: Sequence[Metadata] = [],
    ):
        """Add a select words rapid to the validation set.

        Args:
            asset (MediaAsset | TextAsset): The asset for the rapid.
            instruction (str): The instruction for the rapid.
            select words (list[str]): The select words for the rapid.
            truths (list[int]): The list of indices of the true word selections.
            strict_grading (bool | None, optional): The strict grading for the rapid. Defaults to None.
            metadata (Sequence[Metadata], optional): The metadata for the rapid.

        Returns:
            ValidationSetBuilder: The ValidationSetBuilder instance.

        Raises:
            ValueError: If a correct word is not found in the select words.
        """
        transcription_words = [
            TranscriptionWord(word=word, wordIndex=i)
            for i, word in enumerate(select_words.split())
        ]

        true_words = []
        for idx in truths:
            if idx > len(transcription_words) - 1:
                raise ValueError(f"Index {idx} is out of bounds")
            true_words.append(transcription_words[idx])

        payload = TranscriptionPayload(
            _t="TranscriptionPayload", title=instruction, transcription=transcription_words
        )

        model_truth = TranscriptionTruth(
            _t="TranscriptionTruth",
            correctWords=true_words,
            strictGrading=strict_grading,
        )

        self._rapid_parts.append(
            ValidatioRapidParts(
                instruction=instruction,
                asset=asset,
                payload=payload,
                truths=model_truth,
                metadata=metadata,
                randomCorrectProbability = 1 / len(transcription_words),
            )
        )