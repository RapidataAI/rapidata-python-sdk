import logging
import time
from rapidata import logger
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from rapidata import __version__

# Initialize OTLP logging with error handling
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
    otlp_handler = LoggingHandler(logger_provider=logger_provider)
    otlp_handler.setLevel(logging.DEBUG)  # OTLP gets everything

    # Console handler - only WARNING and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Console gets WARNING+
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # Configure the logger
    logger.setLevel(logging.DEBUG)  # Logger must allow DEBUG for OTLP

    # Remove any existing handlers (like the default console handler)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add both handlers
    logger.addHandler(otlp_handler)
    logger.addHandler(console_handler)

    print("OTLP logging initialized successfully")
except Exception as e:
    print(f"Warning: Failed to initialize OTLP logging: {e}")
    import traceback

    traceback.print_exc()

# Test logging - you'll see the difference in output
logger.debug("This DEBUG message goes to OTLP only")
logger.info("This INFO message goes to OTLP only")
logger.warning("This WARNING message goes to OTLP AND console")
logger.error("This ERROR message goes to OTLP AND console")
