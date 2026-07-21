from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar, Generic, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError

T = TypeVar("T")


@dataclass
class FailedUpload(Generic[T]):
    """
    Represents a failed upload with the item and error details.

    Attributes:
        item: The item that failed to upload.
        error_message: The error message describing the failure reason.
        error_type: The type of the exception (e.g., "RapidataError").
        timestamp: Optional timestamp when the failure occurred.
        exception: Optional original exception for richer error context.
        trace_id: Optional backend trace ID, when the failure originated from a
            RapidataError whose response included a traceId. Used to correlate
            an SDK-side failure with the backend trace that produced it.
        stage: Optional ingestion stage that failed, for remote-URL assets
            (e.g. "download", "content_type", "timeout", "size", "internal").
            Only "internal" indicates a Rapidata-side fault; every other stage
            is caller-actionable.
        http_status: Optional origin-server HTTP status, when the failure was an
            HTTP response from the asset host (e.g. a 403 on the URL). Distinct
            from any status of the Rapidata API call itself.
    """

    item: T
    error_message: str
    error_type: str
    timestamp: Optional[datetime] = field(default_factory=datetime.now)
    exception: Optional[Exception] = None
    trace_id: Optional[str] = None
    stage: Optional[str] = None
    http_status: Optional[int] = None

    @classmethod
    def from_exception(cls, item: T, exception: Exception | None) -> FailedUpload[T]:
        """
        Create a FailedUpload from an item and exception.

        For RapidataError exceptions, extracts the clean API error reason, the
        backend trace ID, and the structured ingestion stage / origin HTTP
        status (when present in the error response). For other exceptions, uses
        the string representation.

        Args:
            item: The item that failed to upload.
            exception: The exception that occurred.

        Returns:
            FailedUpload instance with error details extracted from the exception.
        """
        if exception is None:
            return cls(
                item=item,
                error_message="Unknown error",
                error_type="Unknown",
                exception=None,
            )

        from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError

        error_type = type(exception).__name__
        trace_id: Optional[str] = None
        stage: Optional[str] = None
        http_status: Optional[int] = None

        if isinstance(exception, RapidataError):
            error_message = exception.get_reason()
            if isinstance(exception.details, dict):
                raw_trace_id = exception.details.get("traceId")
                if isinstance(raw_trace_id, str) and raw_trace_id:
                    trace_id = raw_trace_id

                # stage / upstreamHttpStatus are ProblemDetails extension
                # members the asset service adds for remote-URL ingestion
                # failures; they serialize flat alongside title / traceId.
                raw_stage = exception.details.get("stage")
                if isinstance(raw_stage, str) and raw_stage:
                    stage = raw_stage

                raw_http_status = exception.details.get("upstreamHttpStatus")
                if isinstance(raw_http_status, int):
                    http_status = raw_http_status
        else:
            error_message = str(exception)

        return cls(
            item=item,
            error_message=error_message,
            error_type=error_type,
            exception=exception,
            trace_id=trace_id,
            stage=stage,
            http_status=http_status,
        )

    def format_error_details(self) -> str:
        """
        Format error details for logging or display.

        Returns:
            Formatted string with all error details including timestamp.
        """
        details = [
            f"Item: {self.item}",
            f"Error Type: {self.error_type}",
            f"Error Message: {self.error_message}",
        ]

        if self.stage:
            details.append(f"Stage: {self.stage}")

        if self.http_status is not None:
            details.append(f"HTTP Status: {self.http_status}")

        if self.trace_id:
            details.append(f"Trace Id: {self.trace_id}")

        if self.timestamp:
            details.append(f"Timestamp: {self.timestamp.isoformat()}")

        return "\n".join(details)

    def __str__(self) -> str:
        return f"{self.item}"
