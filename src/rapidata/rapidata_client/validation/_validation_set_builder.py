import os
from rapidata.api_client.models.attach_category_truth import AttachCategoryTruth
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.api_client.models.compare_payload import ComparePayload
from rapidata.api_client.models.compare_truth import CompareTruth
from rapidata.api_client.models.transcription_payload import TranscriptionPayload
from rapidata.api_client.models.transcription_truth import TranscriptionTruth
from rapidata.api_client.models.transcription_word import TranscriptionWord
from rapidata.api_client.models.locate_payload import LocatePayload
from rapidata.api_client.models.locate_box_truth import LocateBoxTruth
from rapidata.api_client.models.line_payload import LinePayload
from rapidata.api_client.models.bounding_box_truth import BoundingBoxTruth
from rapidata.api_client.models.box_shape import BoxShape
from rapidata.rapidata_client.validation.rapidata_validation_set import (
    RapidataValidationSet,
)
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.validation._validation_rapid_parts import ValidatioRapidParts
from rapidata.rapidata_client.metadata._base_metadata import Metadata
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.validation.rapids.box import Box

from rapidata.rapidata_client.validation.rapids.rapids import (
    Rapid, 
    ClassificationRapid,
    CompareRapid,
    SelectWordsRapid,
    LocateRapid,
    DrawRapid
)
from typing import Sequence


class ValidationSetBuilder:
    """The ValidationSetBuilder is used to build a validation set.
    Give the validation set a name and then add classify, compare, or transcription rapid parts to it.
    Get a `ValidationSetBuilder` by calling [`rapi.new_validation_set()`](../rapidata_client.md/#rapidata.rapidata_client.rapidata_client.RapidataClient.new_validation_set).

    Args:
        name (str): The name of the validation set.
        openapi_service (OpenAPIService): An instance of OpenAPIService to interact with the API.
    """

    def __init__(self, name: str, openapi_service: OpenAPIService):
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
        
        elif isinstance(rapid, ClassificationRapid):
            self.__add_classify_rapid(rapid.asset, rapid.instruction, rapid.answer_options, rapid.truths, rapid.metadata)

        elif isinstance(rapid, CompareRapid):
            self.__add_compare_rapid(rapid.asset, rapid.instruction, rapid.truth, rapid.metadata)

        elif isinstance(rapid, SelectWordsRapid):
            self.__add_select_words_rapid(rapid.asset, rapid.instruction, rapid.sentence, rapid.truths, rapid.strict_grading)
        
        elif isinstance(rapid, LocateRapid):
            self.__add_locate_rapid(rapid.asset, rapid.instruction, rapid.truths)

        elif isinstance(rapid, DrawRapid):
            self.__add_draw_rapid(rapid.asset, rapid.instruction, rapid.truths)

        else:
            raise ValueError("Unsupported rapid type")

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
        if not all(truth in answer_options for truth in truths):
            raise ValueError("Truths must be part of the answer options")

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
            assert isinstance(idx, int), "truths must be a list of integers"
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
    
    def __add_locate_rapid(
        self,
        asset: MediaAsset,
        instruction: str,
        truths: list[Box]
    ):
        """Add a locate rapid to the validation set.

        Args:
            instruction (str): The instruction for the locate rapid.
            asset (MediaAsset): The asset for the rapid.
            truths (list[Box]): The truths for the rapid.

        Returns:
            ValidationSetBuilder: The ValidationSetBuilder instance.
        """
        payload = LocatePayload(
            _t="LocatePayload", target=instruction
        )

        img_dimensions = asset.get_image_dimension()

        if not img_dimensions:
            raise ValueError("Failed to get image dimensions")

        model_truth = LocateBoxTruth(
            _t="LocateBoxTruth", 
            boundingBoxes=[BoxShape(
                _t="BoxShape",
                xMin=truth.x_min / img_dimensions[0] * 100,
                xMax=truth.x_max / img_dimensions[0] * 100,
                yMax=truth.y_max / img_dimensions[1] * 100,
                yMin=truth.y_min / img_dimensions[1] * 100,
            ) for truth in truths]
        )

        coverage = self._calculate_boxes_coverage(truths, img_dimensions[0], img_dimensions[1])

        self._rapid_parts.append(
            ValidatioRapidParts(
                instruction=instruction,
                payload=payload,
                truths=model_truth,
                metadata=[],
                randomCorrectProbability=coverage,
                asset=asset,
            )
        )

    def __add_draw_rapid(
        self,
        asset: MediaAsset,
        instruction: str,
        truths: list[Box]
    ):
        """Add a draw rapid to the validation set.

        Args:
            instruction (str): The instruction for the draw rapid.
            asset (MediaAsset): The asset for the rapid.
            truths (list[Box]): The truths for the rapid.

        Returns:
            ValidationSetBuilder: The ValidationSetBuilder instance.
        """

        payload = LinePayload(
            _t="LinePayload", target=instruction
        )

        img_dimensions = asset.get_image_dimension()

        if not img_dimensions:
            raise ValueError("Failed to get image dimensions")

        model_truth = BoundingBoxTruth(
            _t="BoundingBoxTruth", 
            xMax=truths[0].x_max / img_dimensions[0],
            xMin=truths[0].x_min / img_dimensions[0],
            yMax=truths[0].y_max / img_dimensions[1],
            yMin=truths[0].y_min / img_dimensions[1],
        ) # TO BE CHANGED BEFORE MERGING

        coverage = self._calculate_boxes_coverage(truths, img_dimensions[0], img_dimensions[1])

        self._rapid_parts.append(
            ValidatioRapidParts(
                instruction=instruction,
                payload=payload,
                truths=model_truth,
                metadata=[],
                randomCorrectProbability=coverage,
                asset=asset,
            )
        )


    def _calculate_boxes_coverage(self, boxes: list[Box], image_width: int, image_height: int) -> float:
        if not boxes:
            return 0.0
            
        # Convert all coordinates to integers for pixel-wise coverage
        pixels = set()
        for box in boxes:
            for x in range(int(box.x_min), int(box.x_max + 1)):
                for y in range(int(box.y_min), int(box.y_max + 1)):
                    if 0 <= x < image_width and 0 <= y < image_height:
                        pixels.add((x,y))
                        
        total_covered = len(pixels)
        return total_covered / (image_width * image_height)
