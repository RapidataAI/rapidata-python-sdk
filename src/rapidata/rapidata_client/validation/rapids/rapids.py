from rapidata.api_client import ClassifyPayload
from rapidata.rapidata_client import assets
from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.assets.data_type_enum import RapidataDataTypes
from rapidata.rapidata_client.metadata import Metadata
from typing import Sequence
from rapidata.rapidata_client.validation.rapids.box import Box
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

from rapidata.api_client.models.datapoint_metadata_model_metadata_inner import (
    DatapointMetadataModelMetadataInner,
)


class Rapid():
    def __init__(self, asset: MediaAsset | TextAsset | MultiAsset, metadata: Sequence[Metadata], payload: Any, truth: Any, randomCorrectProbability: float, reasoning: str | None):
        self.asset = asset
        self.metadata = metadata
        self.payload = payload
        self.truth = truth
        self.randomCorrectProbability = randomCorrectProbability
        self.reasoning = reasoning

    def get_media_type(self):
        asset = self.asset.assets[0] if isinstance(self.asset, MultiAsset) else self.asset;
        if isinstance(asset, TextAsset):
            return RapidataDataTypes.TEXT;
        if isinstance(asset, MediaAsset):
            return RapidataDataTypes.MEDIA;

        raise TypeError("Invalid Asset to check")

    def to_media_model(self, validationSetId: str) -> tuple[AddValidationRapidModel, list[str | tuple[str, bytes]]]:
        assets: list[MediaAsset] = [] 
        if isinstance(self.asset, MultiAsset):
            for asset in self.asset.assets:
                if isinstance(asset, MediaAsset):
                    assets.append(asset)
                else:
                    raise TypeError("The asset is a multiasset, but not all assets are MediaAssets")

        if isinstance(self.asset, TextAsset):
            raise TypeError("The asset must contain Media")

        if isinstance(self.asset, MediaAsset):
            assets = [self.asset]

        return (AddValidationRapidModel(
            validationSetId=validationSetId,
            payload=AddValidationRapidModelPayload(self.payload),
            truth=AddValidationRapidModelTruth(self.truth),
            metadata=[
              DatapointMetadataModelMetadataInner(meta._to_model())
              for meta in self.metadata
            ],
            randomCorrectProbability=self.randomCorrectProbability,
            reasoning=self.reasoning
        ), [self._convert_asset(asset) for asset in assets])

    def _convert_asset(self, asset: MediaAsset) -> str | tuple[str, bytes]:
        if isinstance(asset.path, str):
            return asset.path
        elif isinstance(asset.path, bytes):
            return (asset.name, asset.path)
        else:
            raise ValueError("upload file failed")

    def to_text_model(self, validationSetId: str) -> AddValidationTextRapidModel:
        texts: list[str] = []
        if isinstance(self.asset, MultiAsset):
            for asset in self.asset.assets:
                if isinstance(asset, TextAsset):
                    texts.append(asset.text)
                else:
                    raise TypeError("The asset is a multiasset, but not all assets are TextAssets")

        if isinstance(self.asset, MediaAsset):
            raise TypeError("The asset must contain Text")

        if isinstance(self.asset, TextAsset):
            texts = [self.asset.text]

        return AddValidationTextRapidModel(
          validationSetId=validationSetId,
          payload=AddValidationRapidModelPayload(self.payload),
          truth=AddValidationRapidModelTruth(self.truth),
          metadata=[
              DatapointMetadataModelMetadataInner(meta._to_model())
              for meta in self.metadata
          ],
          randomCorrectProbability=self.randomCorrectProbability,
          texts=texts,
          reasoning=self.reasoning
      )


class ClassificationRapid(Rapid):
    """
    A classification rapid. Used as a multiple choice question for the labeler to answer.
    
    
    Args: 
        instruction (str): The instruction how to choose the options.
        answer_options (list[str]): The options that the labeler can choose from.
        truths (list[str]): The correct answers to the question.
        asset (MediaAsset | TextAsset): The asset that the labeler will be labeling.
        metadata (Sequence[Metadata]): The metadata that is attached to the rapid.
    """

    def __init__(self, instruction: str, answer_options: list[str], truths: list[str], asset: MediaAsset | TextAsset, metadata: Sequence[Metadata], reasoning: str | None = None):
        self.instruction = instruction
        self.answer_options = answer_options
        self.truths = truths
        self.asset = asset
        self.metadata = metadata
        self.reasoning = reasoning

class CompareRapid(Rapid):
    """
    Used as a comparison of two assets for the labeler to compare.
    
    Args:
        instruction (str): The instruction that the labeler will be comparing the assets on.
        truth (str): The correct answer to the comparison. (has to be one of the assets)
        asset (MultiAsset): The assets that the labeler will be comparing.
        metadata (Sequence[Metadata]): The metadata that is attached to the rapid.
    """
    def __init__(self, instruction: str, truth: str, asset: MultiAsset, metadata: Sequence[Metadata]):
        self.instruction = instruction
        self.asset = asset
        self.truth = truth
        self.metadata = metadata

class SelectWordsRapid(Rapid):
    """
    Used to give the labeler a text and have them select words from it.
    
    Args:
        instruction (str): The instruction for the labeler.
        truths (list[int]): The indices of the words that are the correct answers.
        asset (MediaAsset): The asset that the labeler will be selecting words from.
        sentence (str): The sentence that the labeler will be selecting words from. (split up by spaces)
        strict_grading (bool): Whether the grading should be strict or not. 
            True means that all correct words and no wrong words have to be selected for the rapid to be marked as correct.
            False means that at least one correct word and no wrong words have to be selected for the rapid to be marked as correct.
    """
    def __init__(self, instruction: str, truths: list[int], asset: MediaAsset, sentence: str, required_precision: float, required_completeness: float, metadata: Sequence[Metadata]):
        if not isinstance(truths, list):
            raise ValueError("The truths must be a list of integers.")
        if not all(isinstance(x, int) for x in truths):
            raise ValueError("The truths must be a list of integers.")
        if required_completeness <= 0 or required_completeness > 1:
            raise ValueError("The required completeness must be > 0 and <= 1.")
        if required_precision <= 0 or required_precision > 1:
            raise ValueError("The required precision must be > 0 and <= 1.")
        
        self.instruction = instruction
        self.truths = truths
        self.asset = asset
        self.sentence = sentence
        self.required_precision = required_precision
        self.required_completeness = required_completeness
        self.metadata = metadata

class LocateRapid(Rapid):
    """
    Used to have the labeler locate a specific object in an image.
    
    Args:
        instruction (str): The instructions on what the labeler should do.
        truths (list[Box]): The boxes that the object is located in.
        asset (MediaAsset): The image that the labeler is locating the object in.
        metadata (Sequence[Metadata]): The metadata that is attached to the rapid.    
    """
    def __init__(self, instruction: str, truths: list[Box], asset: MediaAsset, metadata: Sequence[Metadata]):
        self.instruction = instruction
        self.asset = asset
        self.truths = truths
        self.metadata = metadata

class DrawRapid(Rapid):
    """
    Used to have the labeler draw a specific object in an image.
    
    Args:
        instruction (str): The instructions on what the labeler should do.
        truths (list[Box]): The boxes that the object is located in.
        asset (MediaAsset): The image that the labeler is drawing the object in.
        metadata (Sequence[Metadata]): The metadata that is attached to the rapid.
    """
    def __init__(self, instruction: str, truths: list[Box], asset: MediaAsset, metadata: Sequence[Metadata]):
        self.instruction = instruction
        self.asset = asset
        self.truths = truths
        self.metadata = metadata

class TimestampRapid(Rapid):
    """
    Used to have the labeler timestamp a video or audio file.
    
    Args:
        instruction (str): The instruction for the labeler.
        truths (list[tuple[int, int]]): The possible accepted timestamps intervals for the labeler (in miliseconds).
            The first element of the tuple is the start of the interval and the second element is the end of the interval.
        asset (MediaAsset): The asset that the labeler is timestamping.
        metadata (Sequence[Metadata]): The metadata that is attached to the rapid.
    """
    def __init__(self, instruction: str, truths: list[tuple[int, int]], asset: MediaAsset, metadata: Sequence[Metadata]):
        if not asset.get_duration():
            raise ValueError("The datapoints must have a duration. (e.g. video or audio)")
        
        if not isinstance(truths, list):
            raise ValueError("The truths must be a list of tuples.")

        for truth in truths:
            if len(truth) != 2 or not all(isinstance(x, int) for x in truth):
                raise ValueError("The truths per datapoint must be a tuple of exactly two integers.")
            if truth[0] >= truth[1]:
                raise ValueError("The start of the interval must be smaller than the end of the interval.")
            if truth[0] < 0:
                raise ValueError("The start of the interval must be greater than or equal to 0.")
            if truth[1] > asset.get_duration():
                raise ValueError("The end of the interval can not be greater than the duration of the datapoint.")
            
        self.instruction = instruction
        self.truths = truths
        self.asset = asset
        self.metadata = metadata
