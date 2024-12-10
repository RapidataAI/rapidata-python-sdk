from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.metadata import Metadata
from typing import Sequence

class Rapid:
    pass

class ClassificationRapid(Rapid):
    """A classification rapid. Used as a multiple choice question for the labeler to answer."""
    def __init__(self, question: str, options: list[str], truths: list[str], asset: MediaAsset | TextAsset, metadata: Sequence[Metadata]):
        """Creating the classification rapid
        
        Args: 
            question (str): The question to be asked to the labeler.
            options (list[str]): The options that the labeler can choose from.
            truths (list[str]): The correct answers to the question.
            asset (MediaAsset | TextAsset): The asset that the labeler will be labeling.
            metadata (Sequence[Metadata]): The metadata that is attached to the rapid."""
        self.question = question
        self.options = options
        self.truths = truths
        self.asset = asset
        self.metadata = metadata

class CompareRapid(Rapid):
    """A comparison rapid. Used as a comparison of two assets for the labeler to compare."""
    def __init__(self, criteria: str, truth: str, asset: MultiAsset, metadata: Sequence[Metadata]):
        """Creating the comparison rapid

        Args:
            criteria (str): The criteria that the labeler will be comparing the assets on.
            truth (str): The correct answer to the comparison. (has to be one of the assets)
            asset (MultiAsset): The assets that the labeler will be comparing.
            metadata (Sequence[Metadata]): The metadata that is attached to the rapid."""
        self.criteria = criteria
        self.asset = asset
        self.truth = truth
        self.metadata = metadata

class SelectWordsRapid(Rapid):
    """A select words rapid. Used to give the labeler a text and have them select words from it."""
    def __init__(self, instruction: str, truths: list[int], asset: MediaAsset, sentence: str, strict_grading: bool):
        """Creating the select words rapid
        
        Args:
            instruction (str): The instruction for the labeler.
            truths (list[int]): The indices of the words that are the correct answers.
            asset (MediaAsset): The asset that the labeler will be selecting words from.
            sentence (str): The sentence that the labeler will be selecting words from. (split up by spaces)
            strict_grading (bool): Whether the grading should be strict or not. 
                True means that all correct words and no wrong words have to be selected for the rapid to be marked as correct.
                False means that at least one correct word and no wrong words have to be selected for the rapid to be marked as correct."""
        self.instruction = instruction
        self.truths = truths
        self.asset = asset
        self.sentence = sentence
        self.strict_grading = strict_grading

