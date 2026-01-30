from pathlib import Path
import shutil
from pydantic import BaseModel, ConfigDict, Field, field_validator
from rapidata.rapidata_client.config import logger


class UploadConfig(BaseModel):
    """
    Holds the configuration for the upload process.

    Attributes:
        maxWorkers (int): The maximum number of worker threads for concurrent uploads. Defaults to 25.
        maxRetries (int): The maximum number of retries for failed uploads. Defaults to 3.
        cacheToDisk (bool): Enable disk-based caching for file uploads. If False, uses in-memory cache only. Defaults to True.
            Note: URL assets are always cached in-memory regardless of this setting.
            Caching cannot be disabled entirely as it's required for the two-step upload flow.
        cacheTimeout (float): Cache operation timeout in seconds. Defaults to 0.1.
        cacheLocation (Path): Directory for cache storage. Defaults to ~/.cache/rapidata/upload_cache.
            This is immutable. Only used for file uploads when cacheToDisk=True.
        cacheShards (int): Number of cache shards for parallel access. Defaults to 128.
            Higher values improve concurrency but increase file handles. Must be positive.
            This is immutable. Only used for file uploads when cacheToDisk=True.
        enableBatchUpload (bool): Enable batch URL uploading (two-step process). Defaults to True.
        batchSize (int): Number of URLs per batch (100-5000). Defaults to 1000.
        batchPollInterval (float): Polling interval in seconds. Defaults to 0.5.
    """

    model_config = ConfigDict(validate_assignment=True)

    maxWorkers: int = Field(default=25)
    maxRetries: int = Field(default=3)
    cacheToDisk: bool = Field(
        default=True,
        description="Enable disk-based caching for file uploads. URLs are always cached in-memory.",
    )
    cacheTimeout: float = Field(default=1)
    cacheLocation: Path = Field(
        default=Path.home() / ".cache" / "rapidata" / "upload_cache",
        frozen=True,
    )
    cacheShards: int = Field(
        default=128,
        frozen=True,
    )
    batchSize: int = Field(
        default=1000,
        description="Number of URLs per batch (100-5000)",
    )
    batchPollInterval: float = Field(
        default=0.5,
        description="Polling interval in seconds",
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

    @field_validator("batchSize")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if v < 100:
            raise ValueError("batchSize must be at least 100")
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
