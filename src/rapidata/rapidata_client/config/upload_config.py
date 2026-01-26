from pathlib import Path
import threading
from typing import Callable
from pydantic import BaseModel, Field, field_validator
from rapidata.rapidata_client.config import logger

# Type alias for config update handlers
UploadConfigUpdateHandler = Callable[["UploadConfig"], None]

# Global list to store registered handlers with thread-safe access
_handlers_lock = threading.Lock()
_upload_config_handlers: list[UploadConfigUpdateHandler] = []


def register_upload_config_handler(handler: UploadConfigUpdateHandler) -> None:
    """Register a handler to be called when the upload configuration updates."""
    with _handlers_lock:
        _upload_config_handlers.append(handler)


def unregister_upload_config_handler(handler: UploadConfigUpdateHandler) -> None:
    """Unregister a previously registered handler."""
    with _handlers_lock:
        if handler in _upload_config_handlers:
            _upload_config_handlers.remove(handler)


class UploadConfig(BaseModel):
    """
    Holds the configuration for the upload process.

    Attributes:
        maxWorkers (int): The maximum number of worker threads for concurrent uploads. Defaults to 25.
        maxRetries (int): The maximum number of retries for failed uploads. Defaults to 3.
        cacheUploads (bool): Enable/disable upload caching. Defaults to True.
        cacheTimeout (float): Cache operation timeout in seconds. Defaults to 0.1.
        cacheLocation (Path): Directory for cache storage. Defaults to ~/.rapidata/upload_cache.
        cacheSizeLimit (int): Maximum total cache size in bytes. Defaults to 100MB.
        cacheShards (int): Number of cache shards for parallel access. Defaults to 128.
            Higher values improve concurrency but increase file handles. Must be positive.
    """

    maxWorkers: int = Field(default=25)
    maxRetries: int = Field(default=3)
    cacheUploads: bool = Field(default=True)
    cacheTimeout: float = Field(default=0.1)
    cacheLocation: Path = Field(default=Path.home() / ".rapidata" / "upload_cache")
    cacheSizeLimit: int = Field(default=100_000_000)  # 100MB
    cacheShards: int = Field(default=128)

    @field_validator("maxWorkers")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        if v > 200:
            logger.warning(
                f"maxWorkers is set to {v}, which is above the recommended limit of 200. "
                "This may lead to suboptimal performance due to connection pool constraints."
            )
        return v

    @field_validator("cacheShards")
    @classmethod
    def validate_cache_shards(cls, v: int) -> int:
        if v < 1:
            raise ValueError("cacheShards must be at least 1")
        if v & (v - 1) != 0:
            logger.warning(
                f"cacheShards={v} is not a power of 2. Power-of-2 values provide better hash distribution."
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
        # Snapshot handlers under lock to prevent modifications during iteration
        with _handlers_lock:
            handlers = _upload_config_handlers.copy()

        # Execute handlers outside lock to avoid deadlocks
        for handler in handlers:
            try:
                handler(self)
            except Exception as e:
                logger.warning(f"Warning: UploadConfig handler failed: {e}")
