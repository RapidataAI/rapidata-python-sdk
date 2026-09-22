from typing import Protocol, runtime_checkable, Any
import threading
import platform
import sys
import os
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from rapidata import __version__
from .logging_config import LoggingConfig, register_config_handler
from rapidata.rapidata_client.config import logger


def get_system_attributes() -> dict[str, str | int | None]:
    """Gather system telemetry for traces."""
    try:
        attrs = {
            "system.os": platform.system(),
            "system.os.version": platform.release(),
            "system.arch": platform.machine(),
            "python.version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "process.cpu_count": os.cpu_count(),
        }
        logger.debug(f"System attributes: {attrs}")
        return attrs
    except Exception:
        logger.debug("Failed to get system attributes, returning empty dict")
        return {}


@runtime_checkable
class TracerProtocol(Protocol):
    """Protocol that defines the tracer interface for type checking."""

    def activate(self) -> None: ...
    def start_span(self, name: str, *args, **kwargs) -> Any: ...
    def start_as_current_span(self, name: str, *args, **kwargs) -> Any: ...
    def set_session_id(self, session_id: str) -> None: ...
    def set_user_info(self, client_id: str, email: str) -> None: ...
    def fail_current_span(self, message: str | None = None) -> None: ...


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

    def activate(self) -> None:
        pass

    def start_span(self, name: str, *args, **kwargs) -> NoOpSpan:
        return NoOpSpan()

    def start_as_current_span(self, name: str, *args, **kwargs) -> NoOpSpan:
        return NoOpSpan()

    def set_session_id(self, session_id: str) -> None:
        pass

    def set_user_info(self, client_id: str, email: str) -> None:
        pass

    def fail_current_span(self, message: str | None = None) -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        """Delegate to no-op behavior."""
        return lambda *args, **kwargs: NoOpSpan()


class SpanContextManagerWrapper:
    """Wrapper for span context managers to add session_id on enter."""

    def __init__(
        self,
        context_manager: Any,
        session_id: str | None,
        client_id: str | None = None,
        email: str | None = None,
    ):
        self._context_manager = context_manager
        self.session_id = session_id
        self.client_id = client_id
        self.email = email

    def __enter__(self):
        span = self._context_manager.__enter__()
        if hasattr(span, "set_attribute"):
            if self.session_id:
                span.set_attribute("SDK.session.id", self.session_id)
            if self.client_id:
                span.set_attribute("identity", self.client_id)
            if self.email:
                span.set_attribute("email", self.email)
        return span

    def __exit__(self, *args):
        return self._context_manager.__exit__(*args)


class RapidataTracer:
    """Tracer implementation that updates when the configuration changes.

    Spans are no-ops until ``activate()`` is called, which RapidataClient does
    on construction. SDK components built directly against a mocked service, as
    test suites do, therefore never reach the collector.
    """

    def __init__(self, name: str = __name__):
        self._name = name
        self._otlp_initialized = False
        self._init_lock = threading.Lock()
        self._tracer_provider = None
        self._real_tracer = None
        self._no_op_tracer = NoOpTracer()
        self._enabled = True  # Default to enabled
        self._activated = False
        self._environment = "rapidata.ai"
        self.session_id: str | None = None
        self.client_id: str | None = None
        self.email: str | None = None

        # Register this tracer to receive configuration updates
        register_config_handler(self._handle_config_update)

    def _handle_config_update(self, config: LoggingConfig) -> None:
        """Handle configuration updates."""
        self._update_tracer(config)

    def _update_tracer(self, config: LoggingConfig) -> None:
        """Update the tracer based on the new configuration."""
        self._enabled = config.enable_otlp
        self._environment = config.environment

    def activate(self) -> None:
        """Allow spans to be exported from this process."""
        self._activated = True

    def _exporting(self) -> bool:
        """Return True when spans should go to the real tracer."""
        if not (self._enabled and self._activated):
            return False
        self._ensure_initialized()
        return self._real_tracer is not None

    def _ensure_initialized(self) -> None:
        """Lazily initialize OTLP tracing on first use."""
        if self._otlp_initialized:
            return

        with self._init_lock:
            if self._otlp_initialized:
                return

            try:
                resource_attributes = {
                    "service.name": "Rapidata.Python.SDK",
                    "service.version": __version__,
                    **get_system_attributes(),
                }

                resource = Resource.create(resource_attributes)

                self._tracer_provider = TracerProvider(resource=resource)

                exporter = OTLPSpanExporter(
                    endpoint=f"https://otlp-sdk.{self._environment}/v1/traces",
                    timeout=30,
                )

                span_processor = BatchSpanProcessor(exporter)
                self._tracer_provider.add_span_processor(span_processor)

                self._real_tracer = self._tracer_provider.get_tracer(self._name)
                self._otlp_initialized = True

            except Exception as e:
                logger.warning(f"Failed to initialize tracing: {e}")
                self._enabled = False

    def _add_attributes_to_span(self, span: Any) -> Any:
        """Add session and user attributes to a span."""
        if hasattr(span, "set_attribute"):
            if self.session_id:
                span.set_attribute("SDK.session.id", self.session_id)
            if self.client_id:
                span.set_attribute("identity", self.client_id)
            if self.email:
                span.set_attribute("email", self.email)
        return span

    def start_span(self, name: str, *args, **kwargs) -> Any:
        """Start a span, or return a no-op span if tracing is disabled."""
        if self._exporting():
            assert self._real_tracer is not None
            span = self._real_tracer.start_span(name, *args, **kwargs)
            return self._add_attributes_to_span(span)
        return self._no_op_tracer.start_span(name, *args, **kwargs)

    def start_as_current_span(self, name: str, *args, **kwargs) -> Any:
        """Start a span as current, or return a no-op span if tracing is disabled."""
        if self._exporting():
            assert self._real_tracer is not None
            context_manager = self._real_tracer.start_as_current_span(
                name, *args, **kwargs
            )
            return SpanContextManagerWrapper(
                context_manager, self.session_id, self.client_id, self.email
            )
        return self._no_op_tracer.start_as_current_span(name, *args, **kwargs)

    def set_session_id(self, session_id: str) -> None:
        self.session_id = session_id
        logger.debug(f"Session ID set to: {self.session_id}")

    def set_user_info(self, client_id: str, email: str) -> None:
        self.client_id = client_id
        self.email = email
        logger.debug(
            f"User info set - client_id: {self.client_id}, email: {self.email}"
        )

    def fail_current_span(self, message: str | None = None) -> None:
        """Mark the current span as errored."""
        span = trace.get_current_span()
        if span.is_recording():
            span.set_status(Status(StatusCode.ERROR, message))

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the appropriate tracer."""
        if self._exporting():
            return getattr(self._real_tracer, name)
        return getattr(self._no_op_tracer, name)


# Create the main tracer instance - type checkers will see it as TracerProtocol
tracer: TracerProtocol = RapidataTracer()  # type: ignore[assignment]
