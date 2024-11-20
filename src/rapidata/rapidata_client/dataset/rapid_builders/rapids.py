from rapidata.rapidata_client.assets import MediaAsset, TextAsset, MultiAsset
from rapidata.rapidata_client.metadata import Metadata, TranscriptionMetadata

class Rapid:
    pass

class ClassificationRapid(Rapid):
    def __init__(self, question: str, options: list[str], truths: list[str], asset: MediaAsset | TextAsset, metadata: list[Metadata]):
        self.question = question
        self.options = options
        self.truths = truths
        self.asset = asset

        self.metadata = metadata

class CompareRapid(Rapid):
    def __init__(self, criteria: str, truth: str, asset: MultiAsset, metadata: list[Metadata]):
        self.criteria = criteria
        self.asset = asset
        self.truth = truth
        self.metadata = metadata

class TranscriptionRapid(Rapid):
    def __init__(self, instruction: str, truths: list[int], asset: MediaAsset, transcription: str, strict_grading: bool):
        self.instruction = instruction
        self.truths = truths
        self.asset = asset
        self.transcription = transcription
        self.strict_grading = strict_grading

