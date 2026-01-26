from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar, Generic, TYPE_CHECKING

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
    """

    item: T
    error_message: str
    error_type: str

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
        )

    def __str__(self) -> str:
        return f"{self.item}"
