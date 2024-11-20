from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets import MediaAsset, TextAsset
from rapidata.rapidata_client.metadata import PromptMetadata
from rapidata.rapidata_client.dataset.rapidata_validation_set import RapidataValidationSet
from rapidata.rapidata_client.dataset.rapid_builders.rapids import ClassificationRapid

class ClassifyRapidBuilder:
    def __init__(self, question: str, options: list[str], truths: list[str], asset: MediaAsset | TextAsset):
        self._question = question
        self._options = options
        self._truths = truths
        self._asset = asset
        self._metadata = []

    def prompt(self, prompt: str):
        self._metadata.append(PromptMetadata(prompt))
        return self
    
    def build(self):
        return ClassificationRapid(
            question=self._question,
            options=self._options,
            truths=self._truths,
            asset=self._asset,
            metadata=self._metadata
        )
    
class ClassifyRapidTruthBuilder:
    def __init__(self, question: str, options: list[str], asset: MediaAsset | TextAsset):
        self._question = question
        self._options = options
        self._asset = asset
        self._truths = None

    def truths(self, truths: list[str]):
        self._truths = truths
        return self._build()
    
    def _build(self):
        if self._truths is None:
            raise ValueError("Truths are required")
        return ClassifyRapidBuilder(
            question=self._question,
            options=self._options,
            asset=self._asset,
            truths=self._truths,
        )
    
class ClassifyRapidMediaBuilder:
    def __init__(self, question: str, options: list[str], ):
        self._question = question
        self._options = options
        self._asset: MediaAsset | TextAsset | None = None

    def media(self, media: str):
        if not isinstance(media, str):
            raise ValueError("Media must be a string, either a local file path or an image URL")
        
        self._asset = MediaAsset(media)

        return self._build()

    def text(self, text: str):
        if not isinstance(text, str):
            raise ValueError("Text must be a string")
        
        self._asset = TextAsset(text)

        return self._build()

    def _build(self):
        if self._asset is None:
            raise ValueError("Assets are required")
        
        return ClassifyRapidTruthBuilder(
            question=self._question,
            options=self._options,
            asset=self._asset,
        )

class ClassifyRapidOptionsBuilder:
    def __init__(self, question: str):
        self._question = question
        self._options = None

    def options(self, options: list[str]):
        self._options = options
        return self._build()
    
    def _build(self):
        if self._options is None:
            raise ValueError("Options are required")
        
        return ClassifyRapidMediaBuilder(
            question=self._question,
            options=self._options,
        )


class ClassifyRapidQuestionBuilder:
    def __init__(self):
        self._question = None

    def question(self, question: str):
        self._question = question
        return self._build()
    
    def _build(self):
        if self._question is None:
            raise ValueError("Question is required")
        
        return ClassifyRapidOptionsBuilder(
            question=self._question,
        )
