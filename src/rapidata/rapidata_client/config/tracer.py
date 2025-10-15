from contextlib import contextmanager
from typing import Protocol, runtime_checkable, Any
from opentelemetry import trace, context
from opentelemetry.trace import SpanContext, TraceFlags
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
    def create_root_context(self, name: str) -> None: ...


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

    def start_as_current_span(self, name: str, *args, **kwargs):
        yield NoOpSpan()

    def create_root_context(self, name: str) -> None:
        pass

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
        self._enabled = True
        self._root_span = None
        self._root_context = None
        self._context_token = None

        register_config_handler(self._handle_config_update)

    def _handle_config_update(self, config: LoggingConfig) -> None:
        """Handle configuration updates."""
        self._update_tracer(config)

    def _update_tracer(self, config: LoggingConfig) -> None:
        """Update the tracer based on the new configuration."""
        self._enabled = config.enable_otlp

        if not self._otlp_initialized and config.enable_otlp:
            try:
                resource = Resource.create(
                    {
                        "service.name": "Rapidata.Python2.SDK",
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

    def create_root_context(self, name: str) -> None:
        """Create a root span and set it as the active context for all future spans."""
        if self._enabled and self._real_tracer:
            # End previous root span if it exists
            if self._root_span:
                self._root_span.end()
            if self._context_token:
                context.detach(self._context_token)

            # Create new root span
            self._root_span = self._real_tracer.start_span(name)
            self._root_context = trace.set_span_in_context(self._root_span)
            # Attach it so all subsequent spans are children
            self._context_token = context.attach(self._root_context)
            logger.debug(f"Created root context: {name}")

    def start_span(self, name: str, *args, **kwargs) -> Any:
        """Start a span (will automatically be a child of root if root context exists)."""
        if self._enabled and self._real_tracer:
            return self._real_tracer.start_span(name, *args, **kwargs)
        return self._no_op_tracer.start_span(name, *args, **kwargs)

    @contextmanager
    def start_as_current_span(self, name: str, *args, **kwargs):
        """Start a span as current (will automatically be a child of root if root context exists)."""
        if self._enabled and self._real_tracer:
            with self._real_tracer.start_as_current_span(name, *args, **kwargs) as span:
                try:
                    yield span
                finally:
                    # After the span ends, recreate root with same trace ID
                    if self._root_span:
                        # Get the trace ID from the current root span
                        trace_id = self._root_span.get_span_context().trace_id

                        # End the old root span
                        self._root_span.end()

                        # Detach the old context
                        if self._context_token:
                            context.detach(self._context_token)

                        # Create new root span with same trace ID
                        self._root_span = self._real_tracer.start_span(
                            name="root_span",  # or whatever name you want
                            context=trace.set_span_in_context(
                                trace.NonRecordingSpan(
                                    SpanContext(
                                        trace_id=trace_id,
                                        span_id=0,  # This will be generated
                                        is_remote=False,
                                        trace_flags=TraceFlags(0x01),
                                    )
                                )
                            ),
                        )
                        self._root_context = trace.set_span_in_context(self._root_span)
                        self._context_token = context.attach(self._root_context)
        else:
            yield from self._no_op_tracer.start_as_current_span(name, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the appropriate tracer."""
        if self._enabled and self._real_tracer:
            return getattr(self._real_tracer, name)
        return getattr(self._no_op_tracer, name)


# Create the main tracer instance - type checkers will see it as TracerProtocol
tracer: TracerProtocol = RapidataTracer()  # type: ignore[assignment]
