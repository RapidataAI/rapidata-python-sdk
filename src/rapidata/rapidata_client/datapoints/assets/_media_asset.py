"""Media Asset Module with Lazy Loading

Defines the MediaAsset class for handling media file paths within assets.
Implements lazy loading for URL-based media to prevent unnecessary downloads.
"""

from typing import Optional, cast
import os
from io import BytesIO
from rapidata.rapidata_client.datapoints.assets._base_asset import BaseAsset
import requests
import re
from PIL import Image
from tinytag import TinyTag
import tempfile
from pydantic import StrictStr, StrictBytes
import logging
from functools import cached_property
from rapidata.rapidata_client.datapoints.assets._sessions import SessionManager
from rapidata.rapidata_client.logging import logger

class MediaAsset(BaseAsset):
    """MediaAsset Class with Lazy Loading

    Represents a media asset by storing the file path or URL.
    Only downloads URL content when needed.
    Supports local files and URLs for images, MP3, and MP4.

    Args:
        path (str): The file system path to the media asset or URL.

    Raises:
        FileNotFoundError: If the provided file path does not exist.
    """
    _logger = logging.getLogger(__name__ + '.MediaAsset')

    ALLOWED_TYPES = [
        'image/', 
        'audio/mp3',      # MP3
        'video/mp4',       # MP4
    ]

    MIME_TYPES = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'mp3': 'audio/mp3',
        'mp4': 'video/mp4'
    }

    FILE_SIGNATURES = {
        b'\xFF\xD8\xFF': 'image/jpeg',
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'GIF87a': 'image/gif',
        b'GIF89a': 'image/gif',
        b'RIFF': 'image/webp',
        b'ID3': 'audio/mp3',
        b'\xFF\xFB': 'audio/mp3',
        b'\xFF\xF3': 'audio/mp3',
        b'ftyp': 'video/mp4',
    }

    def __init__(self, path: str):
        """
        Initialize a MediaAsset instance.

        Args:
            path (str): The file system path to the media asset or a URL.

        Raises:
            FileNotFoundError: If the provided file path does not exist.
            ValueError: If path is not a string.
        """
        if not isinstance(path, str):
            raise ValueError(f"Media must be a string, either a local file path or a URL, got {type(path)}")
        
        self._url = None
        self._content = None
        self.session: requests.Session  = SessionManager.get_session()
        
        if re.match(r'^https?://', path):
            self._url = path
            self.name = path.split('/')[-1]
            self.name = self.__check_name_ending(self.name)
            self.path = path
            return
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        
        self.path = path
        self.name = path

    @cached_property
    def content(self) -> bytes:
        """
        Lazy loader for URL content. Only downloads when first accessed.
        Uses cached_property to store the result after first download.
        """
        if self._url is None:
            self.path = cast(str, self.path)
            with open(self.path, 'rb') as f:
                return f.read()
            
        return self.__get_media_bytes(self._url)

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
        
        # Return 0 for static images
        if any(path_to_check.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            return 0

        try:
            # Create temporary file from content
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(self.name)[1], delete=False) as tmp:
                tmp.write(self.content)
                tmp.flush()
                tmp_path = tmp.name
                
            try:
                tag = TinyTag.get(tmp_path)
            finally:
                # Clean up the temporary file
                os.unlink(tmp_path)
            
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
            img = Image.open(BytesIO(self.content))
            return img.size
        except Exception:
            return None

    def set_custom_name(self, name: str) -> 'MediaAsset':
        """Set a custom name for the media asset (only works with URLs)."""
        if self._url is not None:
            self.name = self.__check_name_ending(name)
        else:
            raise ValueError("Custom name can only be set for URLs.")
        return self
    
    def __check_name_ending(self, name: str) -> str:
        """Check if the media path is valid."""
        if not name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.webp')):
            logger.warning("Warning: Supported file types: jpg, jpeg, png, gif, mp3, mp4. Image might not be displayed correctly.")
            name = name + '.jpg'
        return name

    def __get_media_type_from_extension(self, url: str) -> Optional[str]:
        """
        Determine media type from URL file extension.
        
        Args:
            url: The URL to check
            
        Returns:
            Optional[str]: MIME type if valid extension found, None otherwise
        """
        try:
            ext = url.lower().split('?')[0].split('.')[-1]
            return self.MIME_TYPES.get(ext)
        except IndexError:
            return None
        
    def __validate_image_content(self, content: bytes) -> bool:
        """
        Validate image content using PIL.
        
        Args:
            content: Image bytes to validate
            
        Returns:
            bool: True if valid image, False otherwise
        """
        try:
            img = Image.open(BytesIO(content))
            img.verify()
            return True
        except Exception as e:
            self._logger.debug(f"Image validation failed: {str(e)}")
            return False
        
    def __get_media_type_from_signature(self, content: bytes) -> Optional[str]:
        """
        Determine media type from file signature.
        
        Args:
            content: File content bytes
            
        Returns:
            Optional[str]: MIME type if valid signature found, None otherwise
        """
        file_start = content[:32]
        for signature, mime_type in self.FILE_SIGNATURES.items():
            if file_start.startswith(signature) or (signature in file_start[:10]):
                return mime_type
        return None

    def __get_media_bytes(self, url: str) -> bytes:
        """
        Downloads and validates media files from URL with retry logic and session reuse.
        
        Args:
            url: URL of the media file
            
        Returns:
            bytes: Validated media content
            
        Raises:
            ValueError: If media type is unsupported or content validation fails
            requests.exceptions.RequestException: If download fails after all retries
        """
        # Use existing session or throw error if not set
        if self.session is None:
            raise RuntimeError("HTTP session not configured")

        try:
            response = self.session.get(
                url, 
                stream=False,
                timeout=(5, 30)  # (connect timeout, read timeout)
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Failed to download media from {url} after retries: {str(e)}")
            raise

        content = response.content
        content_type = response.headers.get('content-type', '').lower()

        # Case 1: Content-type is already allowed
        if any(content_type.startswith(t) for t in self.ALLOWED_TYPES):
            self._logger.debug(f"Content-type {content_type} is allowed")
            return content

        # Case 2: Try to validate based on extension
        mime_type = self.__get_media_type_from_extension(url)
        if mime_type and mime_type.startswith(tuple(self.ALLOWED_TYPES)):
            self._logger.debug(f"Found valid mime type from extension: {mime_type}")
            return content

        # Case 3: Try to validate based on file signature
        mime_type = self.__get_media_type_from_signature(content)
        if mime_type and mime_type.startswith(tuple(self.ALLOWED_TYPES)):
            self._logger.debug(f"Found valid mime type from signature: {mime_type}")
            return content

        # Case 4: Last resort - try direct image validation
        if self.__validate_image_content(content):
            self._logger.debug("Content validated as image through direct validation")
            return content

        # If we get here, validation failed
        error_msg = (
            f'Could not validate media type from content.\n'
            f'Content-Type: {content_type}\n'
            f'URL extension: {url.split("?")[0].split(".")[-1]}\n'
            f'Allowed types: {self.ALLOWED_TYPES}'
        )
        self._logger.error(error_msg)
        raise ValueError(error_msg)
    
    def is_local(self) -> bool:
        """Check if the media asset is a local file."""
        return self._url is None
    
    def to_file(self) -> StrictStr | tuple[StrictStr, StrictBytes] | StrictBytes:
        """Convert the media asset to a file representation."""
        if self._url is None:
            self.path = cast(str, self.path)
            return self.path
        else:
            return (self.name, self.content)
        
    def __str__(self) -> str:
        return f"MediaAsset(path={self.path})"
    
    def __repr__(self) -> str:
        return f"MediaAsset(path={self.path})"
