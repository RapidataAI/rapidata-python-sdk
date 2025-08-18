from typing import Callable
from pydantic import BaseModel, Field

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
    """

    level: str = Field(default="WARNING")
    log_file: str | None = Field(default=None)
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    silent_mode: bool = Field(default=False)
    enable_otlp: bool = Field(default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._notify_handlers()

    def __setattr__(self, name: str, value) -> None:
        super().__setattr__(name, value)
        self._notify_handlers()

    def _notify_handlers(self) -> None:
        """Notify all registered handlers that the configuration has updated."""
        for handler in _config_handlers:
            try:
                handler(self)
            except Exception as e:
                # Log the error but don't let one handler failure break others
                print(f"Warning: Config handler failed: {e}")


# Tracer is now handled in tracer.py with event-based updates
