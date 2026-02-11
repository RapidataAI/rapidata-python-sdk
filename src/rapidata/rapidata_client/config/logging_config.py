from __future__ import annotations

import os
from typing import Any, Callable

from pydantic import BaseModel, Field, model_validator

from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config._env_utils import apply_env_overrides


def _default_enable_otlp() -> bool:
    """Return the default for enable_otlp, respecting the RAPIDATA_DISABLE_OTLP env var."""
    return os.environ.get("RAPIDATA_DISABLE_OTLP", "0").lower() not in ("1", "true", "yes")

# Type alias for config update handlers
ConfigUpdateHandler = Callable[["LoggingConfig"], None]

# Global list to store registered handlers
_config_handlers: list[ConfigUpdateHandler] = []


def register_config_handler(handler: ConfigUpdateHandler) -> None:
    """Register a handler to be called when the logging configuration updates."""
    _config_handlers.append(handler)


def unregister_config_handler(handler: ConfigUpdateHandler) -> None:
    """Unregister a previously registered handler."""
    if handler in _config_handlers:
        _config_handlers.remove(handler)


class LoggingConfig(BaseModel):
    """
    Holds the configuration for the logging process.

    Attributes:
        level (str): The logging level. Defaults to "WARNING".
        log_file (str | None): The logging file. Defaults to None.
        format (str): The logging format. Defaults to "%(asctime)s - %(name)s - %(levelname)s - %(message)s".
        silent_mode (bool): Whether to disable the prints and progress bars. Does NOT affect the logging. Defaults to False.
        enable_otlp (bool): Whether to enable OpenTelemetry trace logs. Defaults to True.
            Can also be disabled via the RAPIDATA_DISABLE_OTLP=1 environment variable.
    """

    @model_validator(mode="before")
    @classmethod
    def _apply_env_vars(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return apply_env_overrides(cls.model_fields, data)
        return data

    level: str = Field(default="WARNING")
    log_file: str | None = Field(default=None)
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    silent_mode: bool = Field(default=False)
    enable_otlp: bool = Field(default_factory=_default_enable_otlp)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._notify_handlers()

    def __setattr__(self, name: str, value) -> None:
        super().__setattr__(name, value)
        # Sync enable_otlp to env var so child processes (e.g. Ray workers) inherit it
        if name == "enable_otlp":
            if value:
                os.environ.pop("RAPIDATA_DISABLE_OTLP", None)
            else:
                os.environ["RAPIDATA_DISABLE_OTLP"] = "1"
        self._notify_handlers()

    def _notify_handlers(self) -> None:
        """Notify all registered handlers that the configuration has updated."""
        for handler in _config_handlers:
            try:
                handler(self)
            except Exception as e:
                logger.warning(f"Warning: Config handler failed: {e}")
