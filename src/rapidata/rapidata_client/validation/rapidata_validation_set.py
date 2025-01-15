import os
from typing import Any
from rapidata.api_client.models.add_validation_rapid_model import (
    AddValidationRapidModel,
)
from rapidata.api_client.models.add_validation_text_rapid_model import (
    AddValidationTextRapidModel,
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
from rapidata.api_client.models.scrub_payload import ScrubPayload
from rapidata.api_client.models.scrub_truth import ScrubTruth
from rapidata.rapidata_client.assets._media_asset import MediaAsset
from rapidata.rapidata_client.assets._multi_asset import MultiAsset
from rapidata.rapidata_client.assets._text_asset import TextAsset
from rapidata.rapidata_client.metadata._base_metadata import Metadata
from rapidata.service.openapi_service import OpenAPIService

from typing import Sequence


class RapidataValidationSet:
    """A class for interacting with a Rapidata validation set.

    Represents a set of all the validation tasks that can be added to an order.

    When added to an order, the tasks will be selected randomly from the set.

    Attributes:
        id (str): The ID of the validation set.
        name (str): The name of the validation set.
    """

    def __init__(self, validation_set_id, openapi_service: OpenAPIService, name: str):
        self.id = validation_set_id
        self.name = name
        self.__openapi_service = openapi_service

    def __upload_files(self, model: AddValidationRapidModel, assets: list[MediaAsset]):
        """Upload a file to the validation set.

        Args:
            assets: list[(MediaAsset)]: The asset to upload.
        """
        files = []
        for asset in assets:
            if isinstance(asset.path, str):
                files.append(asset.path)
            elif isinstance(asset.path, bytes):
                files.append((asset.name, asset.path))
            else:
                raise ValueError("upload file failed")
        self.__openapi_service.validation_api.validation_add_validation_rapid_post(
            model=model, files=files
        )        

    def _add_general_validation_rapid(
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
            | ScrubPayload
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
            | ScrubTruth
        ),
        metadata: Sequence[Metadata],
        asset: MediaAsset | TextAsset | MultiAsset,
        randomCorrectProbability: float,
    ) -> None:
        """Add a validation rapid to the validation set.

        Args:
            payload: The payload for the rapid.
            truths: The truths for the rapid.
            metadata (list[Metadata]): The metadata for the rapid.
            asset: The asset(s) for the rapid.
            randomCorrectProbability (float): The random correct probability for the rapid.

        Returns:
            None

        Raises:
            ValueError: If an invalid asset type is provided.
        """

        model = AddValidationRapidModel(
            validationSetId=self.id,
            payload=AddValidationRapidModelPayload(payload),
            truth=AddValidationRapidModelTruth(truths),
            metadata=[
                DatapointMetadataModelMetadataInner(meta._to_model())
                for meta in metadata
            ],
            randomCorrectProbability=randomCorrectProbability,
        )
        if isinstance(asset, MediaAsset):
            self.__upload_files(model=model, assets=[asset])

        elif isinstance(asset, TextAsset):
            model = AddValidationTextRapidModel(
                validationSetId=self.id,
                payload=AddValidationRapidModelPayload(payload),
                truth=AddValidationRapidModelTruth(truths),
                metadata=[
                    DatapointMetadataModelMetadataInner(meta._to_model())
                    for meta in metadata
                ],
                randomCorrectProbability=randomCorrectProbability,
                texts=[asset.text],
            )
            self.__openapi_service.validation_api.validation_add_validation_text_rapid_post(
                add_validation_text_rapid_model=model
            )

        elif isinstance(asset, MultiAsset):
            files = [a for a in asset if isinstance(a, MediaAsset)]
            texts = [a.text for a in asset if isinstance(a, TextAsset)]
            if files:
                self.__upload_files(model=model, assets=files)
            if texts:
                model = AddValidationTextRapidModel(
                    validationSetId=self.id,
                    payload=AddValidationRapidModelPayload(payload),
                    truth=AddValidationRapidModelTruth(truths),
                    metadata=[
                        DatapointMetadataModelMetadataInner(meta._to_model())
                        for meta in metadata
                    ],
                    randomCorrectProbability=randomCorrectProbability,
                    texts=texts,
                )
                self.__openapi_service.validation_api.validation_add_validation_text_rapid_post(
                    add_validation_text_rapid_model=model
                )
                
        else:
            raise ValueError("Invalid asset type")

    def _add_classify_rapid(
        self,
        asset: MediaAsset | TextAsset,
        instruction: str,
        categories: list[str],
        truths: list[str],
        metadata: Sequence[Metadata] = [],
    ) -> None:
        """Add a classify rapid to the validation set.

        Args:
            asset (MediaAsset | TextAsset): The asset for the rapid.
            instruction (str): The instruction for the rapid.
            categories (list[str]): The list of categories for the rapid.
            truths (list[str]): The list of truths for the rapid.
            metadata (Sequence[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            None
        """
        payload = ClassifyPayload(
            _t="ClassifyPayload", possibleCategories=categories, title=instruction
        )
        model_truth = AttachCategoryTruth(
            correctCategories=truths, _t="AttachCategoryTruth"
        )

        self._add_general_validation_rapid(
            payload=payload,
            truths=model_truth,
            metadata=metadata,
            asset=asset,
            randomCorrectProbability=len(truths) / len(categories),
        )

    def _add_compare_rapid(
        self,
        asset: MultiAsset,
        instruction: str,
        truth: str,
        metadata: Sequence[Metadata] = [],
    ) -> None:
        """Add a compare rapid to the validation set.

        Args:
            asset (MultiAsset): The assets for the rapid.
            instruction (str): The instruction for the rapid.
            truth (str): The path to the truth file.
            metadata (Sequence[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            None

        Raises:
            ValueError: If the number of assets is not exactly two.
        """
        payload = ComparePayload(_t="ComparePayload", criteria=instruction)
        # take only last part of truth path
        truth = os.path.basename(truth)
        model_truth = CompareTruth(_t="CompareTruth", winnerId=truth)

        if len(asset) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        self._add_general_validation_rapid(
            payload=payload,
            truths=model_truth,
            metadata=metadata,
            asset=asset,
            randomCorrectProbability=1 / len(asset),
        )

    def _add_transcription_rapid(
        self,
        asset: MediaAsset | TextAsset,
        instruction: str,
        text: list[str],
        correct_words: list[str],
        strict_grading: bool | None = None,
        metadata: Sequence[Metadata] = [],
    ) -> None:
        """Add a transcription rapid to the validation set.

        Args:
            asset (MediaAsset | TextAsset): The asset for the rapid.
            instruction (str): The instruction for the rapid.
            text (list[str]): The text for the rapid.
            correct_words (list[str]): The list of correct words for the rapid.
            strict_grading (bool | None, optional): The strict grading for the rapid. Defaults to None.
            metadata (Sequence[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            None

        Raises:
            ValueError: If a correct word is not found in the transcription.
        """
        transcription_words = [
            TranscriptionWord(word=word, wordIndex=i)
            for i, word in enumerate(text)
        ]

        correct_transcription_words = []
        for word in correct_words:
            if word not in text:
                raise ValueError(f"Correct word '{word}' not found in transcription")
            correct_transcription_words.append(
                TranscriptionWord(word=word, wordIndex=text.index(word))
            )

        payload = TranscriptionPayload(
            _t="TranscriptionPayload", title=instruction, transcription=transcription_words
        )

        model_truth = TranscriptionTruth(
            _t="TranscriptionTruth",
            correctWords=correct_transcription_words,
            strictGrading=strict_grading,
        )

        self._add_general_validation_rapid(
            payload=payload,
            truths=model_truth,
            metadata=metadata,
            asset=asset,
            randomCorrectProbability=len(correct_words) / len(text),
        )

    def __str__(self):
        return f"name: '{self.name}' id: {self.id}"
    
    def __repr__(self):
        return f"name: '{self.name}' id: {self.id}"
