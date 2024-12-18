"""Text Asset Module

Defines the TextAsset class for handling textual data within assets.
"""

from rapidata.rapidata_client.assets._base_asset import BaseAsset


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
            raise ValueError("Text must be a string")
        
        self.text = text
