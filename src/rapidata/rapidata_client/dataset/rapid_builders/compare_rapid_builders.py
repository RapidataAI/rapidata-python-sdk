from rapidata.rapidata_client.assets import MultiAsset, TextAsset, MediaAsset
from rapidata.rapidata_client.metadata import PromptMetadata
from rapidata.rapidata_client.dataset.rapid_builders.rapids import CompareRapid
import re

class CompareRapidBuilder:
    """Final builder class for comparison rapid.
    
    This class handles the final construction of a comparison rapid with all required parameters.
    """
    def __init__(self, criteria: str, truth: str, asset: MultiAsset):
        """Initialize the comparison rapid builder.
        
        Args:
            criteria (str): The criteria for comparison
            truth (str): The correct answer
            asset (MultiAsset): Collection of assets to be compared
        """
        self._criteria = criteria
        self._truth = truth
        self._asset = asset
        self._metadata = []

    def prompt(self, prompt: str):
        """Add a prompt to provide additional context for the comparison.
        
        Args:
            prompt (str): Additional instructions or context
            
        Returns:
            CompareRapidBuilder: The builder instance for method chaining
        """
        self._metadata.append(PromptMetadata(prompt))
        return self

    def build(self):
        """Constructs and returns the final comparison rapid.
        
        Returns:
            CompareRapid: The constructed comparison rapid
        """
        return CompareRapid(
            criteria=self._criteria,
            asset=self._asset,
            truth=self._truth,
            metadata=self._metadata
        )

class CompareRapidTruthBuilder:
    """Builder class for the truth of the comparison rapid.

    This adds the truth to the comparison rapid.    
    """
    def __init__(self, criteria: str, asset: MultiAsset):
        self._criteria = criteria
        self._asset = asset
        self._truth = None
    
    def truth(self, truth: str):
        """Set the truth for the comparison rapid.

        Args:
            truth (str): The correct answer for the comparison task. Is the string of the correct media/text asset"""
        
        if not isinstance(truth, str):
            raise ValueError("Truth must be a string.")
        
        self._truth = MediaAsset(truth).name
        
        return self._build()
    
    def _build(self):
        if self._truth is None:
            raise ValueError("Truth is required")
        
        return CompareRapidBuilder(
            criteria=self._criteria,
            asset=self._asset,
            truth=self._truth,
        )

class CompareRapidAssetBuilder:
    """Builder class for the asset of the comparison rapid.

    This adds the asset to the comparison rapid.
    """
    def __init__(self, criteria: str):
        self._criteria = criteria
        self._asset: MultiAsset | None = None

    def media(self, medias: list[str]):
        """Set the media assets for the comparison rapid.

        Args:
            medias (list[str]): The local file paths or links of the media assets to be compared"""
        
        media_assets = [MediaAsset(media) for media in medias]
        self._asset = MultiAsset(media_assets)
        return self._build()
    
    def text(self, texts: list[str]):
        """Set the text assets for the comparison rapid.

        Args:
            texts (list[str]): The texts to be compared"""
        
        text_assets = [TextAsset(text) for text in texts]
        self._asset = MultiAsset(text_assets)
        return self._build()
    
    def _build(self):
        if self._asset is None:
            raise ValueError("Asset is required")

        return CompareRapidTruthBuilder(
            criteria=self._criteria,
            asset=self._asset,
        )

class CompareRapidCriteriaBuilder:
    """Builder class for the criteria of the comparison rapid.

    This adds the criteria to the comparison rapid."""
    def __init__(self):
        self._criteria = None

    def criteria(self, criteria: str):
        """Set the criteria for the comparison rapid.

        Args:
            criteria (str): The criteria for comparison"""
        
        if not isinstance(criteria, str):
            raise ValueError("Criteria must be a string")
        
        self._criteria = criteria
        return self._build()

    def _build(self):
        if self._criteria is None:
            raise ValueError("Criteria is required")

        return CompareRapidAssetBuilder(
            criteria=self._criteria,
        )
