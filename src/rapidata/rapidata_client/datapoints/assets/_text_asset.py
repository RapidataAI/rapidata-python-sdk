"""Text Asset Module

Defines the TextAsset class for handling textual data within assets.
"""

from rapidata.rapidata_client.datapoints.assets._base_asset import BaseAsset


class TextAsset(BaseAsset):
    """TextAsset Class

    Represents a textual asset.

    Args:
        text (str): The text content of the asset.
    """

    def __init__(self, text: str):
        """
        Initialize a TextAsset instance.

        Args:
            text (str): The textual content of the asset.
        """
        if not isinstance(text, str):
            raise ValueError(f"Text must be a string, got {type(text)}")
        
        self.text = text

    def __str__(self) -> str:
        return f"TextAsset(text={self.text})"
    
    def __repr__(self) -> str:
        return f"TextAsset(text={self.text})"
