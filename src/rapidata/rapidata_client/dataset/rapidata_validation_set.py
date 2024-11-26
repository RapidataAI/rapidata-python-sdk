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
from rapidata.rapidata_client.assets.media_asset import MediaAsset
from rapidata.rapidata_client.assets.multi_asset import MultiAsset
from rapidata.rapidata_client.assets.text_asset import TextAsset
from rapidata.rapidata_client.metadata.base_metadata import Metadata
from rapidata.service.openapi_service import OpenAPIService


class RapidataValidationSet:
    """A class for interacting with a Rapidata validation set.

    Get a `ValidationSet` either by using `rapi.get_validation_set(id)` to get an existing validation set or by using `rapi.new_validation_set(name)` to create a new validation set.
    """

    def __init__(self, validation_set_id, openapi_service: OpenAPIService, name: str):
        self.id = validation_set_id
        self.openapi_service = openapi_service
        self.name = name

    def upload_files(self, model: AddValidationRapidModel, assets: list[MediaAsset]):
        """Upload a file to the validation set.

        Args:
            asset list[(MediaAsset)]: The asset to upload.

        Returns:
            str: The path to the uploaded file.
        """
        files = []
        for asset in assets:
            if isinstance(asset.path, str):
                files.append(asset.path)
            elif isinstance(asset.path, bytes):
                files.append((asset.name, asset.path))
            else:
                raise ValueError("upload file failed")
        self.openapi_service.validation_api.validation_add_validation_rapid_post(
            model=model, files=files
        )        

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
                DatapointMetadataModelMetadataInner(meta.to_model())
                for meta in metadata
            ],
            randomCorrectProbability=randomCorrectProbability,
        )
        if isinstance(asset, MediaAsset):
            self.upload_files(model=model, assets=[asset])

        elif isinstance(asset, TextAsset):
            model = AddValidationTextRapidModel(
                validationSetId=self.id,
                payload=AddValidationRapidModelPayload(payload),
                truth=AddValidationRapidModelTruth(truths),
                metadata=[
                    DatapointMetadataModelMetadataInner(meta.to_model())
                    for meta in metadata
                ],
                randomCorrectProbability=randomCorrectProbability,
                texts=[asset.text],
            )
            self.openapi_service.validation_api.validation_add_validation_text_rapid_post(
                add_validation_text_rapid_model=model
            )

        elif isinstance(asset, MultiAsset):
            files = [a for a in asset if isinstance(a, MediaAsset)]
            texts = [a.text for a in asset if isinstance(a, TextAsset)]
            if files:
                self.upload_files(model=model, assets=files)
            if texts:
                model = AddValidationTextRapidModel(
                    validationSetId=self.id,
                    payload=AddValidationRapidModelPayload(payload),
                    truth=AddValidationRapidModelTruth(truths),
                    metadata=[
                        DatapointMetadataModelMetadataInner(meta.to_model())
                        for meta in metadata
                    ],
                    randomCorrectProbability=randomCorrectProbability,
                    texts=texts,
                )
                self.openapi_service.validation_api.validation_add_validation_text_rapid_post(
                    add_validation_text_rapid_model=model
                )


        else:
            raise ValueError("Invalid asset type")

    def add_classify_rapid(
        self,
        asset: MediaAsset | TextAsset,
        question: str,
        categories: list[str],
        truths: list[str],
        metadata: list[Metadata] = [],
    ) -> None:
        """Add a classify rapid to the validation set.

        Args:
            asset (MediaAsset | TextAsset): The asset for the rapid.
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
            asset=asset,
            randomCorrectProbability=len(truths) / len(categories),
        )

    def add_compare_rapid(
        self,
        asset: MultiAsset,
        question: str,
        truth: str,
        metadata: list[Metadata] = [],
    ) -> None:
        """Add a compare rapid to the validation set.

        Args:
            asset (MultiAsset): The assets for the rapid.
            question (str): The question for the rapid.
            truth (str): The path to the truth file.
            metadata (list[Metadata], optional): The metadata for the rapid. Defaults to an empty list.

        Returns:
            None

        Raises:
            ValueError: If the number of assets is not exactly two.
        """
        payload = ComparePayload(_t="ComparePayload", criteria=question)
        # take only last part of truth path
        truth = os.path.basename(truth)
        model_truth = CompareTruth(_t="CompareTruth", winnerId=truth)

        if len(asset) != 2:
            raise ValueError("Compare rapid requires exactly two media paths")

        self.add_general_validation_rapid(
            payload=payload,
            truths=model_truth,
            metadata=metadata,
            asset=asset,
            randomCorrectProbability=1 / len(asset),
        )

    def add_transcription_rapid(
        self,
        asset: MediaAsset | TextAsset,
        question: str,
        transcription: list[str],
        correct_words: list[str],
        strict_grading: bool | None = None,
        metadata: list[Metadata] = [],
    ) -> None:
        """Add a transcription rapid to the validation set.

        Args:
            asset (MediaAsset | TextAsset): The asset for the rapid.
            question (str): The question for the rapid.
            transcription (list[str]): The transcription for the rapid.
            correct_words (list[str]): The list of correct words for the rapid.
            strict_grading (bool | None, optional): The strict grading for the rapid. Defaults to None.
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
            asset=asset,
            randomCorrectProbability=len(correct_words) / len(transcription),
        )

    def __str__(self):
        return f"name: '{self.name}' id: {self.id}"
    
    def __repr__(self):
        return f"name: '{self.name}' id: {self.id}"
