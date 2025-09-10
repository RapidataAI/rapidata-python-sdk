from typing import Optional, Any
from rapidata.api_client.api_client import (
    ApiClient,
    rest,
    ApiResponse,
    ApiResponseT,
)
from rapidata.api_client.exceptions import ApiException
import json
import threading
from contextlib import contextmanager
from rapidata.rapidata_client.config import logger, tracer
from opentelemetry import trace
from opentelemetry.trace import format_trace_id, format_span_id, Link, SpanContext
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator


# Thread-local storage for controlling error logging
_thread_local = threading.local()


@contextmanager
def suppress_rapidata_error_logging():
    """Context manager to suppress error logging for RapidataApiClient calls."""
    old_value = getattr(_thread_local, "suppress_error_logging", False)
    _thread_local.suppress_error_logging = True
    try:
        yield
    finally:
        _thread_local.suppress_error_logging = old_value


def _should_suppress_error_logging() -> bool:
    """Check if error logging should be suppressed for the current thread."""
    return getattr(_thread_local, "suppress_error_logging", False)


class RapidataError(Exception):
    """Custom error class for Rapidata API errors."""

    def __init__(
        self,
        status_code: Optional[int] = None,
        message: str | None = None,
        original_exception: Exception | None = None,
        details: Any = None,
    ):
        self.status_code = status_code
        self.message = message
        self.original_exception = original_exception
        self.details = details

        # Create a nice error message
        error_msg = "Rapidata API Error"
        if status_code:
            error_msg += f" ({status_code})"
        if message:
            error_msg += f": {message}"

        super().__init__(error_msg)

    def __str__(self):
        """Return a string representation of the error."""
        # Extract information from message if available
        title = None
        errors = None
        trace_id = None

        # Try to extract from details if available and is a dict
        if self.details and isinstance(self.details, dict):
            title = self.details.get("title")
            errors = self.details.get("errors")
            trace_id = self.details.get("traceId")

        # Build the error string
        error_parts = []

        # Main error line
        if title:
            error_parts.append(f"{title}")
        else:
            error_parts.append(f"{self.message or 'Unknown error'}")

        # Reasons
        if errors:
            if isinstance(errors, dict):
                error_parts.append(f"Reasons: {json.dumps({'errors': errors})}")
            else:
                error_parts.append(f"Reasons: {errors}")

        # Trace ID
        if trace_id:
            error_parts.append(f"Trace Id: {trace_id}")
        else:
            error_parts.append("Trace Id: N/A")

        return "\n".join(error_parts)


class RapidataApiClient(ApiClient):
    """Custom API client that wraps errors in RapidataError."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id_generator = RandomIdGenerator()

    def call_api(
        self,
        method,
        url,
        header_params=None,
        body=None,
        post_params=None,
        _request_timeout=None,
    ) -> rest.RESTResponse:
        # Get the current span from OpenTelemetry
        current_span = trace.get_current_span()

        # Initialize header_params if it's None
        if header_params is None:
            header_params = {}

        # Add tracing headers if we have a valid span
        if not current_span.is_recording():
            return super().call_api(
                method,
                url,
                header_params,
                body,
                post_params,
                _request_timeout,
            )

        current_span_context = current_span.get_span_context()

        # Generate a new trace ID for backend communication
        # This separates the backend trace from the SDK trace
        backend_trace_id = self.id_generator.generate_trace_id()
        backend_span_id = self.id_generator.generate_span_id()

        # Create a new span context for the backend trace
        backend_span_context = SpanContext(
            trace_id=backend_trace_id,
            span_id=backend_span_id,
            is_remote=True,
            trace_flags=current_span_context.trace_flags,
        )

        # Create a link from current SDK span to the backend trace
        link_to_backend = Link(backend_span_context)

        # Create a link from backend trace back to the original SDK span
        link_back_to_sdk = Link(current_span_context)

        # Create a span in the current SDK trace that links to the backend
        with tracer.start_span(
            f"{str(method).upper()} {url}",
            links=[link_to_backend],
        ) as sdk_request_span:
            # Set attributes on the SDK span
            sdk_request_span.set_attribute("http.method", method)
            sdk_request_span.set_attribute("http.target", url)
            sdk_request_span.set_attribute(
                "rapidata.backend_trace_id", format_trace_id(backend_trace_id)
            )
            sdk_request_span.set_attribute(
                "rapidata.original_trace_id",
                format_trace_id(current_span_context.trace_id),
            )

            # Now create the initial span for the backend trace that will be sent
            # This span will be the starting point for the backend trace
            with tracer.start_span(
                f"{str(method).upper()} {url}",
                context=trace.set_span_in_context(
                    trace.NonRecordingSpan(backend_span_context)
                ),
                links=[link_back_to_sdk],
            ) as backend_initial_span:
                # Set attributes on the backend initial span
                backend_initial_span.set_attribute("http.method", method)
                backend_initial_span.set_attribute("http.target", url)
                backend_initial_span.set_attribute(
                    "rapidata.trace_type", "backend_start"
                )
                backend_initial_span.set_attribute(
                    "rapidata.sdk_trace_id",
                    format_trace_id(current_span_context.trace_id),
                )

                # Format the traceparent header with the backend trace ID
                # The backend will receive this and continue the trace
                header_params["traceparent"] = (
                    "00-"
                    + format_trace_id(backend_trace_id)
                    + "-"
                    + format_span_id(backend_initial_span.get_span_context().span_id)
                    + "-"
                    + f"{backend_span_context.trace_flags:02x}"
                )

                return super().call_api(
                    method,
                    url,
                    header_params,
                    body,
                    post_params,
                    _request_timeout,
                )

    def response_deserialize(
        self,
        response_data: rest.RESTResponse,
        response_types_map: Optional[dict[str, ApiResponseT]] = None,
    ) -> ApiResponse[ApiResponseT]:
        """Override the response_deserialize method to catch and convert exceptions."""
        try:
            return super().response_deserialize(response_data, response_types_map)
        except ApiException as e:
            status_code = getattr(e, "status", None)
            message = str(e)
            details = None

            # Extract more detailed error message from response body if available
            if hasattr(e, "body") and e.body:
                try:
                    body_json = json.loads(e.body)
                    if isinstance(body_json, dict):
                        if "message" in body_json:
                            message = body_json["message"]
                        elif "error" in body_json:
                            message = body_json["error"]

                        # Store the full error details for debugging
                        details = body_json
                except (json.JSONDecodeError, AttributeError):
                    # If we can't parse the body as JSON, use the original message
                    pass

            error_formatted = RapidataError(
                status_code=status_code,
                message=message,
                original_exception=e,
                details=details,
            )

            # Only log error if not suppressed
            if not _should_suppress_error_logging():
                logger.error("Error: %s", error_formatted)
            else:
                logger.debug("Suppressed Error: %s", error_formatted)

            raise error_formatted from None
