import logging
from typing import Protocol, runtime_checkable
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from rapidata import __version__
from .logging_config import LoggingConfig, register_config_handler


def _create_resilient_session() -> requests.Session:
    """Create a session with connection pooling and retry logic for OTLP log exporter."""
    session = requests.Session()

    # Configure retry strategy - be more lenient for telemetry
    retry_strategy = Retry(
        total=2,  # Only 2 retries for telemetry to avoid delays
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )

    # Mount adapter with connection pooling
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=5,  # Fewer connections for telemetry
        pool_maxsize=10,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol that defines the logger interface for type checking."""

    def debug(self, msg: object, *args, **kwargs) -> None: ...
    def info(self, msg: object, *args, **kwargs) -> None: ...
    def warning(self, msg: object, *args, **kwargs) -> None: ...
    def warn(self, msg: object, *args, **kwargs) -> None: ...
    def error(self, msg: object, *args, **kwargs) -> None: ...
    def exception(self, msg: object, *args, exc_info=True, **kwargs) -> None: ...
    def critical(self, msg: object, *args, **kwargs) -> None: ...
    def fatal(self, msg: object, *args, **kwargs) -> None: ...
    def log(self, level: int, msg: object, *args, **kwargs) -> None: ...
    def isEnabledFor(self, level: int) -> bool: ...
    def getEffectiveLevel(self) -> int: ...
    def setLevel(self, level: int | str) -> None: ...
    def addHandler(self, handler: logging.Handler) -> None: ...
    def removeHandler(self, handler: logging.Handler) -> None: ...
    @property
    def handlers(self) -> list[logging.Handler]: ...
    @property
    def level(self) -> int: ...
    @property
    def name(self) -> str: ...


class RapidataLogger:
    """Logger implementation that updates when the configuration changes."""

    def __init__(self, name: str = "rapidata"):
        self._logger = logging.getLogger(name)
        self._otlp_initialized = False
        self._otlp_handler = None

        # Register this logger to receive configuration updates
        register_config_handler(self._handle_config_update)

    def _handle_config_update(self, config: LoggingConfig) -> None:
        """Handle configuration updates."""
        self._update_logger(config)

    def _update_logger(self, config: LoggingConfig) -> None:
        """Update the logger based on the new configuration."""
        # Initialize OTLP logging only once and only if not disabled
        if not self._otlp_initialized and config.enable_otlp:
            try:
                logger_provider = LoggerProvider(
                    resource=Resource.create(
                        {
                            "service.name": "Rapidata.Python.SDK",
                            "service.version": __version__,
                        }
                    ),
                )
                set_logger_provider(logger_provider)

                # Create exporter with resilient session
                # Lower timeout (10s) to avoid blocking on telemetry
                session = _create_resilient_session()
                exporter = OTLPLogExporter(
                    endpoint="https://otlp-sdk.rapidata.ai/v1/logs",
                    timeout=10,  # Reduced from 30s
                    session=session,
                )

                # Use BatchLogRecordProcessor with longer delays to batch more logs
                # and reduce the number of export calls
                processor = BatchLogRecordProcessor(
                    exporter,
                    max_queue_size=2048,
                    schedule_delay_millis=5000,  # Wait 5s before exporting
                    export_timeout_millis=15000,  # 15s timeout for export
                    max_export_batch_size=512,
                )

                logger_provider.add_log_record_processor(processor)

                # OTLP handler - captures DEBUG and above
                self._otlp_handler = LoggingHandler(logger_provider=logger_provider)
                self._otlp_handler.setLevel(logging.DEBUG)  # OTLP gets everything

                self._otlp_initialized = True
                self._logger.debug("OTLP logging initialized successfully")

            except Exception as e:
                # Use debug level to avoid spam, don't print traceback
                self._logger.debug(f"Failed to initialize OTLP logging (will use local logging only): {e}")

        # Console handler with configurable level
        console_handler = logging.StreamHandler()
        console_level = getattr(logging, config.level.upper())
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter(config.format)
        console_handler.setFormatter(console_formatter)

        # Configure the logger
        self._logger.setLevel(logging.DEBUG)  # Logger must allow DEBUG for OTLP

        # Remove any existing handlers (except OTLP when appropriate)
        for handler in self._logger.handlers[:]:
            if handler != self._otlp_handler:
                self._logger.removeHandler(handler)
            elif handler == self._otlp_handler and not config.enable_otlp:
                self._logger.removeHandler(handler)

        # Add OTLP handler if initialized and not disabled
        if (
            self._otlp_handler
            and self._otlp_handler not in self._logger.handlers
            and config.enable_otlp
        ):
            self._logger.addHandler(self._otlp_handler)

        # Add console handler
        self._logger.addHandler(console_handler)

        # Add file handler if log_file is provided
        if config.log_file:
            file_handler = logging.FileHandler(config.log_file)
            file_handler.setLevel(console_level)  # Use same level as console
            file_formatter = logging.Formatter(config.format)
            file_handler.setFormatter(file_formatter)
            self._logger.addHandler(file_handler)

    def __getattr__(self, name: str) -> object:
        """Delegate attribute access to the underlying logger."""
        return getattr(self._logger, name)


logger: LoggerProtocol = RapidataLogger()  # type: ignore[assignment]
