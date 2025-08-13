import logging
import time
from rapidata import logger
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from rapidata import __version__

# Create shared resource
resource = Resource.create(
    {
        "service.name": "Rapidata.Python.SDK",
        "service.version": __version__,
    }
)

# Initialize tracing
try:
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    # Configure OTLP span exporter
    span_exporter = OTLPSpanExporter(
        endpoint="https://otlp-sdk.rapidata.ai/v1/traces",
        timeout=30,
    )

    span_processor = BatchSpanProcessor(
        span_exporter,
        max_queue_size=2048,
        export_timeout_millis=30000,
        max_export_batch_size=512,
    )
    trace_provider.add_span_processor(span_processor)

    # Get tracer
    tracer = trace.get_tracer(__name__)
    print("OTLP tracing initialized successfully")

except Exception as e:
    print(f"Warning: Failed to initialize OTLP tracing: {e}")
    import traceback

    traceback.print_exc()

# Initialize OTLP logging (your existing code)
try:
    logger_provider = LoggerProvider(resource=resource)
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

    handler = LoggingHandler(logger_provider=logger_provider)
    handler.setLevel(logging.DEBUG)

    rapidata_logger = logging.getLogger("rapidata")
    rapidata_logger.addHandler(handler)
    rapidata_logger.setLevel(logging.DEBUG)

    print("OTLP logging initialized successfully")
except Exception as e:
    print(f"Warning: Failed to initialize OTLP logging: {e}")
    import traceback

    traceback.print_exc()


# Example function with tracing
def process_data(data_id: str, data: dict):
    with tracer.start_as_current_span("process_data") as span:
        # Add attributes to the span
        span.set_attribute("data.id", data_id)
        span.set_attribute("data.size", len(str(data)))

        try:
            # Simulate some work
            with tracer.start_as_current_span("validate_data") as child_span:
                child_span.set_attribute("validation.type", "schema")
                time.sleep(0.1)  # Simulate validation work
                logger.info(f"Validating data {data_id}")

            with tracer.start_as_current_span("transform_data") as child_span:
                child_span.set_attribute("transform.type", "normalize")
                time.sleep(0.2)  # Simulate transformation work
                logger.info(f"Transforming data {data_id}")

            with tracer.start_as_current_span("save_data") as child_span:
                child_span.set_attribute("storage.type", "database")
                time.sleep(0.05)  # Simulate save work
                logger.info(f"Saved data {data_id}")

            span.set_attribute("processing.status", "success")
            logger.info(f"Successfully processed data {data_id}")

        except Exception as e:
            span.set_attribute("processing.status", "error")
            span.set_attribute("error.message", str(e))
            logger.error(f"Failed to process data {data_id}: {e}")
            raise


# Test with traces and logs
with tracer.start_as_current_span("main_operation") as main_span:
    main_span.set_attribute("operation.type", "batch_processing")

    for i in range(5):
        try:
            process_data(f"item_{i}", {"value": i * 10, "type": "test"})
        except Exception as e:
            logger.error(f"Error in main operation: {e}")

# Force flush both logs and traces
try:
    if "logger_provider" in locals():
        logger_provider.force_flush(timeout_millis=5000)
        print("Logs flushed successfully")

    if "trace_provider" in locals():
        trace_provider.force_flush(timeout_millis=5000)
        print("Traces flushed successfully")

except Exception as e:
    print(f"Error flushing telemetry data: {e}")
