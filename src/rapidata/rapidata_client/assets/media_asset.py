"""Media Asset Module

Defines the MediaAsset class for handling media file paths within assets.
"""

import os
from io import BytesIO
from rapidata.rapidata_client.assets.base_asset import BaseAsset
from rapidata.rapidata_client.metadata.prompt_metadata import PromptMetadata
import requests
import re

class MediaAsset(BaseAsset):
    """MediaAsset Class

    Represents a media asset by storing the file path.
    Supports local files and URLs for images, MP3, and MP4.

    Args:
        path (str): The file system path to the media asset.

    Raises:
        FileNotFoundError: If the provided file path does not exist.
    """

    ALLOWED_TYPES = [
        'image/', 
        'audio/mp3',      # MP3
        'video/mp4',       # MP4
    ]

    def __init__(self, path: str, prompt: str | None = None):
        """
        Initialize a MediaAsset instance.

        Args:
            path (str): The file system path to the media asset or a URL.

        Raises:
            FileNotFoundError: If the provided file path does not exist.
            ValueError: If media type is unsupported or duration exceeds 25 seconds.
        """
        if not isinstance(path, str):
            raise ValueError("Media must be a string, either a local file path or a URL")
        
        if not isinstance(prompt, str) and prompt is not None:
            raise ValueError("Prompt must be a string or None")

        self.prompt = PromptMetadata(prompt) if prompt else None
        if re.match(r'^https?://', path):
            self.path = self._get_media_bytes(path)
            self.name = path.split('/')[-1]
            self.name = self._check_name_ending(self.name)
            return
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        self.path: str | bytes = path
        self.name = path
    
    def set_custom_name(self, name: str) -> 'MediaAsset':
        """Set a custom name for the media asset (only works with URLs)."""
        if isinstance(self.path, bytes):
            self.name = self._check_name_ending(name)
        else:
            raise ValueError("Custom name can only be set for URLs.")
        return self
    
    def _check_name_ending(self, name: str) -> str:
        """Check if the media path is valid."""
        if not name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.webp')):
            print("Warning: Supported file types: jpg, jpeg, png, gif, mp3, mp4. Image might not be displayed correctly.")
            name = name + '.jpg'
        return name

    def _get_media_bytes(self, url: str) -> bytes:
        """
        Downloads media files from URL and validates type and duration.
        
        Args:
            url: URL of the media file
                
        Returns:
            bytes: Media data
            
        Raises:
            ValueError: If media type is unsupported or duration exceeds limit
            requests.exceptions.RequestException: If download fails
        """
        response = requests.get(url, stream=False)  # Don't stream, we need full file
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()
        
        # Validate content type
        if not any(content_type.startswith(t) for t in self.ALLOWED_TYPES):
            raise ValueError(
                f'URL does not point to an allowed media type.\n'
                f'Content-Type: {content_type}\n'
                f'Allowed types: {self.ALLOWED_TYPES}'
            )

        content = BytesIO(response.content)
        return content.getvalue()
