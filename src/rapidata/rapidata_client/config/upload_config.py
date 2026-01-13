from pathlib import Path
from typing import Callable
from pydantic import BaseModel, Field, field_validator
from rapidata.rapidata_client.config import logger

# Type alias for config update handlers
UploadConfigUpdateHandler = Callable[["UploadConfig"], None]

# Global list to store registered handlers
_upload_config_handlers: list[UploadConfigUpdateHandler] = []


def register_upload_config_handler(handler: UploadConfigUpdateHandler) -> None:
    """Register a handler to be called when the upload configuration updates."""
    _upload_config_handlers.append(handler)


def unregister_upload_config_handler(handler: UploadConfigUpdateHandler) -> None:
    """Unregister a previously registered handler."""
    if handler in _upload_config_handlers:
        _upload_config_handlers.remove(handler)


class UploadConfig(BaseModel):
    """
    Holds the configuration for the upload process.

    Attributes:
        maxWorkers (int): The maximum number of worker threads for processing media paths. Defaults to 25.
        maxRetries (int): The maximum number of retries for failed uploads. Defaults to 3.
    """

    maxWorkers: int = Field(default=25)
    maxRetries: int = Field(default=3)
    cacheUploads: bool = Field(default=True)
    cacheTimeout: float = Field(default=0.1)
    cacheLocation: Path = Field(default=Path.home() / ".rapidata" / "upload_cache")
    cacheSizeLimit: int = Field(default=100_000_000)  # 100MB

    @field_validator("maxWorkers")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        if v > 200:
            logger.warning(
                f"maxWorkers is set to {v}, which is above the recommended limit of 200. "
                "This may lead to suboptimal performance due to connection pool constraints."
            )
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._notify_handlers()

    def __setattr__(self, name: str, value) -> None:
        super().__setattr__(name, value)
        self._notify_handlers()

    def _notify_handlers(self) -> None:
        """Notify all registered handlers that the configuration has updated."""
        for handler in _upload_config_handlers:
            try:
                handler(self)
            except Exception as e:
                logger.warning(f"Warning: UploadConfig handler failed: {e}")
