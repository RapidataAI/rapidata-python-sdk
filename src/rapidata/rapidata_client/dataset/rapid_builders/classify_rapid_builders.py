from rapidata.rapidata_client.assets import MediaAsset, TextAsset
from rapidata.rapidata_client.metadata import PromptMetadata
from rapidata.rapidata_client.dataset.rapid_builders.rapids import ClassificationRapid

class ClassifyRapidBuilder:
    """Final builder class for classification rapid.
    
    This class handles the final construction of a classification rapid with all required parameters.
    """
    def __init__(self, question: str, options: list[str], truths: list[str], asset: MediaAsset | TextAsset):
        self._question = question
        self._options = options
        self._truths = truths
        self._asset = asset
        self._metadata = []

    def prompt(self, prompt: str):
        """Add a prompt to provide additional context for the classification task.
        
        Args:
            prompt (str): Additional instructions or context
            
        Returns:
            ClassifyRapidBuilder: The builder instance for method chaining
        """
        self._metadata.append(PromptMetadata(prompt))
        return self
    
    def build(self):
        """Constructs and returns the final classification rapid.
        
        Returns:
            ClassificationRapid: The constructed classification rapid 
        """
        return ClassificationRapid(
            question=self._question,
            options=self._options,
            truths=self._truths,
            asset=self._asset,
            metadata=self._metadata
        )
    
class ClassifyRapidTruthBuilder:
    """Builder class for the truths of the classification rapid.

    This adds the truths to the classification rapid.
    """
    def __init__(self, question: str, options: list[str], asset: MediaAsset | TextAsset):
        self._question = question
        self._options = options
        self._asset = asset
        self._truths = None

    def truths(self, truths: list[str]):
        """Set the truths for the classification rapid.

        Args:
            truths (list[str]): The correct answers for the classification task"""
        
        if not isinstance(truths, list) or not all(isinstance(truth, str) for truth in truths):
            raise ValueError("Truths must be a list of strings")
        
        if not all(truth in self._options for truth in truths):
            raise ValueError("Truths must be one of the selectable options")
        
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
    """Builder class for the media asset of the classification rapid.

    This class adds the media asset to the classification rapid.
    """
    def __init__(self, question: str, options: list[str]):
        self._question = question
        self._options = options
        self._asset: MediaAsset | TextAsset | None = None

    def media(self, media: str):
        """Set the media asset for the classification rapid.

        Args:
            media (str): A local file path or an image URL. The image will be displayed with the classification task"""        
        self._asset = MediaAsset(media)

        return self._build()

    def text(self, text: str):
        """Set the text asset for the classification rapid.

        Args:
            text (str): The text to be displayed with the classification task"""
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
        """Set the options for the classification rapid.

        Args:
            options (list[str]): The selectable options for the classification task"""

        if not isinstance(options, list) or not all(isinstance(option, str) for option in options):
            raise ValueError("Options must be a list of strings")
        
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
        """Set the question for the classification rapid.

        Args:
            question (str): The question to be answered by the classification task"""
        
        if not isinstance(question, str):
            raise ValueError("Question must be a string")
        
        self._question = question
        return self._build()
    
    def _build(self):
        if self._question is None:
            raise ValueError("Question is required")
        
        return ClassifyRapidOptionsBuilder(
            question=self._question,
        )
