"""Media Asset Module

Defines the MediaAsset class for handling media file paths within assets.
"""

import os
from rapidata.rapidata_client.assets.base_asset import BaseAsset

class MediaAsset(BaseAsset):
    """MediaAsset Class

    Represents a media asset by storing the file path.

    Args:
        path (str): The file system path to the media asset.

    Raises:
        FileNotFoundError: If the provided file path does not exist.
    """

    def __init__(self, path: str):
        """
        Initialize a MediaAsset instance.

        Args:
            path (str): The file system path to the media asset.

        Raises:
            FileNotFoundError: If the provided file path does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}, please provide a valid local file path.")
        self.path = path
