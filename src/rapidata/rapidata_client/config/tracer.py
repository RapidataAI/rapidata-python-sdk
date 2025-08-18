from typing import Protocol, runtime_checkable, Any, Optional, Sequence
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Link, SpanContext
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from rapidata import __version__
from .logging_config import LoggingConfig, register_config_handler
from rapidata.rapidata_client.config import logger


@runtime_checkable
class TracerProtocol(Protocol):
    """Protocol that defines the tracer interface for type checking."""

    def start_span(self, name: str, *args, **kwargs) -> Any: ...
    def start_as_current_span(self, name: str, *args, **kwargs) -> Any: ...
    def start_linked_span(self, name: str, *args, **kwargs) -> Any: ...
    def start_linked_as_current_span(self, name: str, *args, **kwargs) -> Any: ...


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

    def start_linked_span(self, name: str, *args, **kwargs) -> NoOpSpan:
        return NoOpSpan()

    def start_linked_as_current_span(self, name: str, *args, **kwargs) -> NoOpSpan:
        return NoOpSpan()

    def __getattr__(self, name: str) -> Any:
        """Delegate to no-op behavior."""
        return lambda *args, **kwargs: NoOpSpan()


class RapidataTracer:
    """Tracer implementation that updates when the configuration changes and supports client-controlled linking."""

    def __init__(self, name: str = __name__):
        self._name = name
        self._otlp_initialized = False
        self._tracer_provider = None
        self._real_tracer = None
        self._no_op_tracer = NoOpTracer()
        self._enabled = True  # Default to enabled

        # Client lifetime tracking
        self._lifetime_span_context: Optional[SpanContext] = None
        self._id_generator = RandomIdGenerator()

        # Register this tracer to receive configuration updates
        register_config_handler(self._handle_config_update)

    def set_client_lifetime_context(self, lifetime_span_context: SpanContext) -> None:
        """Set the client lifetime span context for automatic linking."""
        self._lifetime_span_context = lifetime_span_context
        logger.debug("Client lifetime context set for tracing")

    def clear_client_lifetime_context(self) -> None:
        """Clear the client lifetime span context."""
        self._lifetime_span_context = None
        logger.debug("Client lifetime context cleared")

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
                trace.set_tracer_provider(self._tracer_provider)

                exporter = OTLPSpanExporter(
                    endpoint="https://otlp-sdk.rapidata.ai/v1/traces",
                    timeout=30,
                )

                span_processor = BatchSpanProcessor(exporter)
                self._tracer_provider.add_span_processor(span_processor)

                self._real_tracer = trace.get_tracer(self._name)
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

    def start_linked_span(self, name: str, *args, **kwargs) -> Any:
        """Start a span with automatic linking to client lifetime, similar to backend linking."""
        if not self._enabled or not self._real_tracer:
            return self._no_op_tracer.start_span(name, *args, **kwargs)

        if not self._lifetime_span_context:
            # No lifetime context, fall back to normal span
            return self._real_tracer.start_span(name, *args, **kwargs)

        # Create a new trace ID for this operation (similar to backend trace separation)
        operation_trace_id = self._id_generator.generate_trace_id()
        operation_span_id = self._id_generator.generate_span_id()

        # Create a new span context for the operation trace
        operation_span_context = SpanContext(
            trace_id=operation_trace_id,
            span_id=operation_span_id,
            is_remote=False,
            trace_flags=self._lifetime_span_context.trace_flags,
        )

        # Create links between lifetime and operation traces
        link_to_operation = Link(operation_span_context)
        link_back_to_lifetime = Link(self._lifetime_span_context)

        # Create a linking span in the lifetime trace
        with self._real_tracer.start_span(
            f"lifetime_link_{name.replace('.', '_')}",
            context=trace.set_span_in_context(
                trace.NonRecordingSpan(self._lifetime_span_context)
            ),
            links=[link_to_operation],
        ) as lifetime_link_span:
            lifetime_link_span.set_attribute("rapidata.operation_name", name)
            lifetime_link_span.set_attribute("rapidata.trace_type", "lifetime_link")
            lifetime_link_span.set_attribute(
                "rapidata.operation_trace_id", trace.format_trace_id(operation_trace_id)
            )

            # Create the actual operation span in its own trace
            return self._real_tracer.start_span(
                name,
                context=trace.set_span_in_context(
                    trace.NonRecordingSpan(operation_span_context)
                ),
                links=[link_back_to_lifetime],
                *args,
                **kwargs,
            )

    def start_linked_as_current_span(self, name: str, *args, **kwargs) -> Any:
        """Start a span as current with automatic linking to client lifetime."""
        if not self._enabled or not self._real_tracer:
            return self._no_op_tracer.start_as_current_span(name, *args, **kwargs)

        if not self._lifetime_span_context:
            # No lifetime context, fall back to normal span
            return self._real_tracer.start_as_current_span(name, *args, **kwargs)

        # Create a new trace ID for this operation
        operation_trace_id = self._id_generator.generate_trace_id()
        operation_span_id = self._id_generator.generate_span_id()

        # Create a new span context for the operation trace
        operation_span_context = SpanContext(
            trace_id=operation_trace_id,
            span_id=operation_span_id,
            is_remote=False,
            trace_flags=self._lifetime_span_context.trace_flags,
        )

        # Create links
        link_to_operation = Link(operation_span_context)
        link_back_to_lifetime = Link(self._lifetime_span_context)

        # Create a linking span in the lifetime trace
        with self._real_tracer.start_span(
            f"lifetime_link_{name.replace('.', '_')}",
            context=trace.set_span_in_context(
                trace.NonRecordingSpan(self._lifetime_span_context)
            ),
            links=[link_to_operation],
        ) as lifetime_link_span:
            lifetime_link_span.set_attribute("rapidata.operation_name", name)
            lifetime_link_span.set_attribute("rapidata.trace_type", "lifetime_link")
            lifetime_link_span.set_attribute(
                "rapidata.operation_trace_id", trace.format_trace_id(operation_trace_id)
            )

            # Create the actual operation span in its own trace as current
            return self._real_tracer.start_as_current_span(
                name,
                context=trace.set_span_in_context(
                    trace.NonRecordingSpan(operation_span_context)
                ),
                links=[link_back_to_lifetime],
                *args,
                **kwargs,
            )

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the appropriate tracer."""
        if self._enabled and self._real_tracer:
            return getattr(self._real_tracer, name)
        return getattr(self._no_op_tracer, name)


# Create the main tracer instance - type checkers will see it as TracerProtocol
tracer: TracerProtocol = RapidataTracer()  # type: ignore[assignment]
