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
    """

    item: T
    error_message: str
    error_type: str
    timestamp: Optional[datetime] = field(default_factory=datetime.now)
    exception: Optional[Exception] = None

    @classmethod
    def from_exception(cls, item: T, exception: Exception | None) -> FailedUpload[T]:
        """
        Create a FailedUpload from an item and exception.

        For RapidataError exceptions, extracts the clean API error reason.
        For other exceptions, uses the string representation.

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

        if isinstance(exception, RapidataError):
            error_message = exception.get_reason()
        else:
            error_message = str(exception)

        return cls(
            item=item,
            error_message=error_message,
            error_type=error_type,
            exception=exception,
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

        if self.timestamp:
            details.append(f"Timestamp: {self.timestamp.isoformat()}")

        return "\n".join(details)

    def __str__(self) -> str:
        return f"{self.item}"
