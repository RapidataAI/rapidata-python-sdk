import logging
from pydantic import BaseModel, Field
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from rapidata import __version__

# from rapidata.rapidata_client.logging import logger

# Module-level flag to track OTLP initialization
_otlp_initialized = False
_otlp_handler = None

# Create module-level logger
logger = logging.getLogger("rapidata")


class LoggingConfig(BaseModel):
    """
    Holds the configuration for the logging process.

    Args:
        level (str): The logging level. Defaults to "WARNING".
        log_file (str | None): The logging file. Defaults to None.
        format (str): The logging format. Defaults to "%(asctime)s - %(name)s - %(levelname)s - %(message)s".
        silent_mode (bool): Whether to disable the prints and progress bars. Does NOT affect the logging. Defaults to False.
    """

    level: str = Field(default="WARNING")
    log_file: str | None = Field(default=None)
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    silent_mode: bool = Field(default=False)

    def __setattr__(self, name: str, value) -> None:
        super().__setattr__(name, value)
        self._update_logger()

    def _update_logger(self) -> None:
        global _otlp_initialized, _otlp_handler

        # Initialize OTLP logging only once
        if not _otlp_initialized:
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

                exporter = OTLPLogExporter(
                    endpoint="https://otlp-sdk.rapidata.ai/v1/logs",
                    timeout=30,
                )

                processor = BatchLogRecordProcessor(
                    exporter,
                    max_queue_size=2048,
                    export_timeout_millis=30000,
                    max_export_batch_size=512,
                )

                logger_provider.add_log_record_processor(processor)

                # OTLP handler - captures DEBUG and above
                _otlp_handler = LoggingHandler(logger_provider=logger_provider)
                _otlp_handler.setLevel(logging.DEBUG)  # OTLP gets everything

                _otlp_initialized = True

            except Exception as e:
                logger.warning(f"Warning: Failed to initialize OTLP logging: {e}")
                import traceback

                traceback.print_exc()

        # Console handler with configurable level
        console_handler = logging.StreamHandler()
        console_level = getattr(logging, self.level.upper())
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter(self.format)
        console_handler.setFormatter(console_formatter)

        # Configure the logger
        logger.setLevel(logging.DEBUG)  # Logger must allow DEBUG for OTLP

        # Remove any existing handlers (except OTLP)
        for handler in logger.handlers[:]:
            if handler != _otlp_handler:
                logger.removeHandler(handler)

        # Add OTLP handler if initialized
        if _otlp_handler and _otlp_handler not in logger.handlers:
            logger.addHandler(_otlp_handler)

        # Add console handler
        logger.addHandler(console_handler)

        # Add file handler if log_file is provided
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(console_level)  # Use same level as console
            file_formatter = logging.Formatter(self.format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
