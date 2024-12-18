from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.metadata import Metadata
from typing import Sequence
from rapidata.rapidata_client.validation.rapids.box import Box

class Rapid:
    pass

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

    def __init__(self, instruction: str, answer_options: list[str], truths: list[str], asset: MediaAsset | TextAsset, metadata: Sequence[Metadata]):
        self.instruction = instruction
        self.answer_options = answer_options
        self.truths = truths
        self.asset = asset
        self.metadata = metadata

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
    def __init__(self, instruction: str, truths: list[int], asset: MediaAsset, sentence: str, strict_grading: bool):
        self.instruction = instruction
        self.truths = truths
        self.asset = asset
        self.sentence = sentence
        self.strict_grading = strict_grading

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
