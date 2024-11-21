"""Media Asset Module

Defines the MediaAsset class for handling media file paths within assets.
"""

import os
from io import BytesIO
from rapidata.rapidata_client.assets.base_asset import BaseAsset
import requests
import re

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
            path (str): The file system path to the media asset or a link to an image.

        Raises:
            FileNotFoundError: If the provided file path does not exist.
        """
        if not isinstance(path, str):
            raise ValueError("Media must be a string, either a local file path or an image URL")

        if re.match(r'^https?://', path):
            self.path = MediaAsset.get_image_bytes(path)
            self.name = path.split('/')[-1]
            if not self.name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                self.name += '.jpg'
            return
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}, please provide a valid local file path.")
        
        self.path: str | bytes = path
        self.name = path
    
    def set_custom_name(self, name: str) -> 'MediaAsset':
        """
        Set a custom name for the media asset, will only work with links.

        Args:
            name (str): The custom name to be set.
        """
        if isinstance(self.path, bytes):
            if not name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                name += '.jpg'
            self.name = name
        else:
            raise ValueError("Custom name can only be set for links.")
        return self

    @staticmethod
    def get_image_bytes(image_url: str) -> bytes:
        """
        Downloads an image from a URL and converts it to bytes.
        Validates that the URL points to an actual image.
        
        Args:
            image_url (str): URL of the image
            
        Returns:
            bytes: Image data as bytes
            
        Raises:
            ValueError: If URL doesn't point to an image
            requests.exceptions.RequestException: If download fails
        """
        response = requests.get(image_url)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f'URL does not point to an image. Content-Type: {content_type}')
        
        return BytesIO(response.content).getvalue()
