from typing import Protocol, runtime_checkable, Any
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from rapidata import __version__
from .logging_config import LoggingConfig, register_config_handler
from rapidata.rapidata_client.config import logger


@runtime_checkable
class TracerProtocol(Protocol):
    """Protocol that defines the tracer interface for type checking."""

    def start_span(self, name: str, *args, **kwargs) -> Any: ...
    def start_as_current_span(self, name: str, *args, **kwargs) -> Any: ...


class NoOpSpan:
    """A no-op span that does nothing when tracing is disabled."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, *args, **kwargs):
        pass

    def set_status(self, *args, **kwargs):
        pass

    def add_event(self, *args, **kwargs):
        pass

    def end(self, *args, **kwargs):
        pass

    def __getattr__(self, name: str) -> Any:
        """Return self for any method call to maintain chainability."""
        return lambda *args, **kwargs: self


class NoOpTracer:
    """A no-op tracer that returns no-op spans when tracing is disabled."""

    def start_span(self, name: str, *args, **kwargs) -> NoOpSpan:
        return NoOpSpan()

    def start_as_current_span(self, name: str, *args, **kwargs) -> NoOpSpan:
        return NoOpSpan()

    def __getattr__(self, name: str) -> Any:
        """Delegate to no-op behavior."""
        return lambda *args, **kwargs: NoOpSpan()


class RapidataTracer:
    """Tracer implementation that updates when the configuration changes."""

    def __init__(self, name: str = __name__):
        self._name = name
        self._otlp_initialized = False
        self._tracer_provider = None
        self._real_tracer = None
        self._no_op_tracer = NoOpTracer()
        self._enabled = True  # Default to enabled

        # Register this tracer to receive configuration updates
        register_config_handler(self._handle_config_update)

    def _handle_config_update(self, config: LoggingConfig) -> None:
        """Handle configuration updates."""
        self._update_tracer(config)

    def _update_tracer(self, config: LoggingConfig) -> None:
        """Update the tracer based on the new configuration."""
        self._enabled = config.enable_otlp

        # Initialize OTLP tracing only once and only if not disabled
        if not self._otlp_initialized and config.enable_otlp:
            try:
                resource = Resource.create(
                    {
                        "service.name": "Rapidata.Python.SDK",
                        "service.version": __version__,
                    }
                )

                self._tracer_provider = TracerProvider(resource=resource)

                exporter = OTLPSpanExporter(
                    endpoint="https://otlp-sdk.rapidata.ai/v1/traces",
                    timeout=30,
                )

                span_processor = BatchSpanProcessor(exporter)
                self._tracer_provider.add_span_processor(span_processor)

                self._real_tracer = self._tracer_provider.get_tracer(self._name)
                self._otlp_initialized = True

            except Exception as e:
                logger.warning(f"Failed to initialize tracing: {e}")
                self._enabled = False

    def start_span(self, name: str, *args, **kwargs) -> Any:
        """Start a span, or return a no-op span if tracing is disabled."""
        if self._enabled and self._real_tracer:
            return self._real_tracer.start_span(name, *args, **kwargs)
        return self._no_op_tracer.start_span(name, *args, **kwargs)

    def start_as_current_span(self, name: str, *args, **kwargs) -> Any:
        """Start a span as current, or return a no-op span if tracing is disabled."""
        if self._enabled and self._real_tracer:
            return self._real_tracer.start_as_current_span(name, *args, **kwargs)
        return self._no_op_tracer.start_as_current_span(name, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the appropriate tracer."""
        if self._enabled and self._real_tracer:
            return getattr(self._real_tracer, name)
        return getattr(self._no_op_tracer, name)


# Create the main tracer instance - type checkers will see it as TracerProtocol
tracer: TracerProtocol = RapidataTracer()  # type: ignore[assignment]
