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

    # Use HTTP exporter with correct endpoint
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

    handler = LoggingHandler(logger_provider=logger_provider)
    handler.setLevel(logging.DEBUG)

    # Attach OTLP handler to the rapidata logger specifically
    rapidata_logger = logging.getLogger("rapidata")
    rapidata_logger.addHandler(handler)
    rapidata_logger.setLevel(logging.DEBUG)

    print("OTLP logging initialized successfully")
except Exception as e:
    print(f"Warning: Failed to initialize OTLP logging: {e}")
    import traceback

    traceback.print_exc()

# Test logging
for i in range(10):
    logger.error(f"Hello, world! Message {i}")
    time.sleep(0.1)  # Small delay to help with batching

# Force flush
try:
    # logger_provider.force_flush(timeout_millis=5000)
    print("Logs flushed successfully")
except Exception as e:
    print(f"Error flushing logs: {e}")
