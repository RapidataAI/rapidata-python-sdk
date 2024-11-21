from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.metadata import Metadata

class Rapid:
    pass

class ClassificationRapid(Rapid):
    """A classification rapid. This represents the question, options, truths, asset and metadata that will be given to the user."""
    def __init__(self, question: str, options: list[str], truths: list[str], asset: MediaAsset | TextAsset, metadata: list[Metadata]):
        self.question = question
        self.options = options
        self.truths = truths
        self.asset = asset
        self.metadata = metadata

class CompareRapid(Rapid):
    """A comparison rapid. This represents the criteria, asset, truth and metadata that will be given to the user."""
    def __init__(self, criteria: str, truth: str, asset: MultiAsset, metadata: list[Metadata]):
        self.criteria = criteria
        self.asset = asset
        self.truth = truth
        self.metadata = metadata

class TranscriptionRapid(Rapid):
    """A transcription rapid. This represents the instruction, truths, asset, transcription and strict grading that will be given to the user."""
    def __init__(self, instruction: str, truths: list[int], asset: MediaAsset, transcription: str, strict_grading: bool):
        self.instruction = instruction
        self.truths = truths
        self.asset = asset
        self.transcription = transcription
        self.strict_grading = strict_grading

