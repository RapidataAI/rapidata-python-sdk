from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config._env_utils import apply_env_overrides


class CompressionConfig(BaseModel):
    """
    Per-upload override for the asset service's image-compression behaviour.

    Any field left as ``None`` falls back to the value the asset service has
    configured globally. Set ``enabled`` to ``True`` (or ``False``) to force the
    behaviour for this client regardless of the server default. Quality is
    expected in the 1..100 range and ``max_dimension`` must be at least 1; both
    are validated server-side.

    Currently applies to single-asset uploads (file paths and individual URLs
    via the ``/asset/file`` and ``/asset/url`` endpoints). Batched URL uploads
    via the orchestrator's ``/asset/batch-upload`` path will gain the same
    override in a follow-up once the SDK's OpenAPI client is regenerated to
    include the ``compression`` field on the batch input model.

    Attributes:
        enabled (bool | None): Force compression on or off. ``None`` to defer to the server default.
        quality (int | None): WebP quality (1..100) to use when compression runs.
        max_dimension (int | None): Maximum width or height in pixels when compression runs.
    """

    model_config = ConfigDict(validate_assignment=True)

    enabled: bool | None = None
    quality: int | None = None
    max_dimension: int | None = None

    @field_validator("quality")
    @classmethod
    def _validate_quality(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= 100:
            raise ValueError("quality must be between 1 and 100")
        return v

    @field_validator("max_dimension")
    @classmethod
    def _validate_max_dimension(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("max_dimension must be at least 1")
        return v

    def is_set(self) -> bool:
        """
        Whether any field has been overridden from its default of ``None``.
        ``enabled=False`` counts as set — it is the explicit "force compression
        off" request, distinct from "defer to server default".
        """
        return any(
            v is not None for v in (self.enabled, self.quality, self.max_dimension)
        )

    def cache_suffix(self) -> str:
        """
        Stable string used as part of the asset upload cache key so that
        the same source asset uploaded under different compression settings
        does not collide on a single cache entry.

        The separator characters ``|``, ``/`` and ``=`` are reserved — none of
        the existing field types (``bool``, ``int``) can produce them, so the
        suffix round-trips unambiguously. Revisit this if a free-form string
        field is ever added.
        """
        if not self.is_set():
            return ""
        return f"|c={self.enabled}/{self.quality}/{self.max_dimension}"


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
        compression (CompressionConfig | None): Per-upload override for the asset service's
            image-compression behaviour. Defaults to None (use server-side defaults).
        autoShortenContext (bool): When True, a datapoint context longer than the backend's
            maximum length is automatically shortened for the order/job instruction before
            upload. When False (default), an over-long context is left unchanged and a
            warning is logged that the backend would reject it. Defaults to False.
        failureTolerance (float): The fraction of a job's datapoints allowed to fail while
            still creating the job definition (0.0-1.0). 0.0 (default) is strict: any failed
            upload aborts creation so no incomplete definition is left behind, and the failed
            datapoints can be retried into the same dataset. 1.0 creates the definition
            regardless of how many datapoints failed. Overridable per call via the
            ``failure_tolerance`` argument on ``create_*_job_definition``. Defaults to 0.0.
    """

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="before")
    @classmethod
    def _apply_env_vars(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return apply_env_overrides(cls.model_fields, data)
        return data

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
    compression: CompressionConfig | None = Field(
        default=None,
        description="Per-upload override for image compression. None uses server defaults.",
    )
    autoShortenContext: bool = Field(
        default=False,
        description="Automatically shorten over-long datapoint contexts for the instruction before upload.",
    )
    failureTolerance: float = Field(
        default=0.0,
        description="Fraction of a job's datapoints allowed to fail while still creating the definition (0.0-1.0).",
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

    @field_validator("failureTolerance")
    @classmethod
    def validate_failure_tolerance(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("failureTolerance must be between 0.0 and 1.0")
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
