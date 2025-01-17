"""Media Asset Module

Defines the MediaAsset class for handling media file paths within assets.
"""

import os
from io import BytesIO
from rapidata.rapidata_client.assets._base_asset import BaseAsset
import requests
import re
from PIL import Image
from tinytag import TinyTag
import tempfile

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

    def __init__(self, path: str):
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
        
        if re.match(r'^https?://', path):
            self.path = self.__get_media_bytes(path)
            self.name = path.split('/')[-1]
            self.name = self.__check_name_ending(self.name)
            return
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        self.path: str | bytes = path
        self.name = path

    def get_duration(self) -> int:
        """
        Get the duration of audio/video files in milliseconds.
        Returns 0 for static images.

        Returns:
            int: Duration in milliseconds for audio/video, 0 for static images

        Raises:
            ValueError: If the duration cannot be determined
        """
        path_to_check = self.name.lower()
        
        # Return 0 for other static images
        if any(path_to_check.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            return 0

        try:
            # For URL downloads (bytes), write to temporary file first
            if isinstance(self.path, bytes):
                with tempfile.NamedTemporaryFile(suffix=os.path.splitext(self.name)[1], delete=False) as tmp:
                    tmp.write(self.path)
                    tmp.flush()
                    # Close the file so it can be read
                    tmp_path = tmp.name
                
                try:
                    tag = TinyTag.get(tmp_path)
                finally:
                    # Clean up the temporary file
                    os.unlink(tmp_path)
            else:
                # For local files, use path directly
                tag = TinyTag.get(self.path)
            
            if tag.duration is None:
                raise ValueError("Could not read duration from file")
                
            return int(tag.duration * 1000)  # Convert to milliseconds
            
        except Exception as e:
            raise ValueError(f"Could not determine media duration: {str(e)}")

    def get_image_dimension(self) -> tuple[int, int] | None:
        """
        Get the dimensions (width, height) of an image file.
        Returns None for non-image files or if dimensions can't be determined.
        """
        if not any(self.name.lower().endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return None
            
        try:
            if isinstance(self.path, bytes):
                img = Image.open(BytesIO(self.path))
            else:
                img = Image.open(self.path)
            return img.size
        except Exception:
            return None

    def set_custom_name(self, name: str) -> 'MediaAsset':
        """Set a custom name for the media asset (only works with URLs)."""
        if isinstance(self.path, bytes):
            self.name = self.__check_name_ending(name)
        else:
            raise ValueError("Custom name can only be set for URLs.")
        return self
    
    def __check_name_ending(self, name: str) -> str:
        """Check if the media path is valid."""
        if not name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.webp')):
            print("Warning: Supported file types: jpg, jpeg, png, gif, mp3, mp4. Image might not be displayed correctly.")
            name = name + '.jpg'
        return name

    def __get_media_bytes(self, url: str) -> bytes:
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
