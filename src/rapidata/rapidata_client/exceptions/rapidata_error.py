from typing import Optional, Any
import json


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

    def get_reason(self) -> str:
        """Get a concise reason string suitable for grouping and display.

        Returns the most meaningful error reason extracted from the API response.
        """
        if self.details and isinstance(self.details, dict):
            title = self.details.get("title")
            if title:
                return title

        if self.message:
            return self.message

        return "Unknown error"

    def __str__(self):
        """Return a string representation of the error."""
        title = None
        errors = None
        trace_id = None

        if self.details and isinstance(self.details, dict):
            title = self.details.get("title")
            errors = self.details.get("errors")
            trace_id = self.details.get("traceId")

        error_parts = []

        if title:
            error_parts.append(f"{title}")
        else:
            error_parts.append(f"{self.message or 'Unknown error'}")

        if errors:
            if isinstance(errors, dict):
                error_parts.append(f"Reasons: {json.dumps({'errors': errors})}")
            else:
                error_parts.append(f"Reasons: {errors}")

        if trace_id:
            error_parts.append(f"Trace Id: {trace_id}")
        else:
            error_parts.append("Trace Id: N/A")

        # Lazy import to avoid a module-level cycle between the exceptions
        # package and the api package.
        from rapidata.rapidata_client.api.rapidata_api_client import (
            format_outdated_sdk_note,
        )
        note = format_outdated_sdk_note()
        if note:
            error_parts.append(note)

        return "\n".join(error_parts)
