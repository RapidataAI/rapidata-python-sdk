from pathlib import Path
import shutil
from pydantic import BaseModel, Field, field_validator
from rapidata.rapidata_client.config import logger


class UploadConfig(BaseModel):
    """
    Holds the configuration for the upload process.

    Attributes:
        maxWorkers (int): The maximum number of worker threads for concurrent uploads. Defaults to 25.
        maxRetries (int): The maximum number of retries for failed uploads. Defaults to 3.
        cacheUploads (bool): Enable/disable upload caching. Defaults to True.
        cacheTimeout (float): Cache operation timeout in seconds. Defaults to 0.1.
        cacheLocation (Path): Directory for cache storage. Defaults to ~/.cache/rapidata/upload_cache.
            This is immutable
        cacheShards (int): Number of cache shards for parallel access. Defaults to 128.
            Higher values improve concurrency but increase file handles. Must be positive.
            This is immutable
    """

    maxWorkers: int = Field(default=25)
    maxRetries: int = Field(default=3)
    cacheUploads: bool = Field(default=True)
    cacheTimeout: float = Field(default=0.1)
    cacheLocation: Path = Field(
        default=Path.home() / ".cache" / "rapidata" / "upload_cache",
        frozen=True,
    )
    cacheShards: int = Field(
        default=128,
        frozen=True,
    )

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
        self._migrate_cache()

    def _migrate_cache(self) -> None:
        """Migrate the cache from the old location to the new location."""
        old_cache = Path.home() / ".rapidata" / "upload_cache"
        new_cache = self.cacheLocation
        if old_cache.exists() and not new_cache.exists():
            try:
                logger.info(f"Migrating cache from {old_cache} to {self.cacheLocation}")
                self.cacheLocation.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_cache), str(self.cacheLocation))

                # Clean up old directory if empty
                if old_cache.parent.exists() and not any(old_cache.parent.iterdir()):
                    old_cache.parent.rmdir()
                logger.info("Cache migration completed successfully")
            except Exception as e:
                logger.warning(
                    f"Failed to migrate cache from {old_cache} to {new_cache}: {e}. "
                    "Starting with empty cache. You may want to manually move the old cache."
                )
