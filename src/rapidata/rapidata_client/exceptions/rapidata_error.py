from __future__ import annotations

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
        trace_id: str | None = None,
    ):
        self.status_code = status_code
        self.message = message
        self.original_exception = original_exception
        self.details = details
        # The problem+json body is the canonical source, but a gateway timeout
        # (408) or an LB-generated error has no body to carry it — then the
        # response header is the only place the id survives.
        self.trace_id = self._trace_id_from_details(details) or trace_id

        # Create a nice error message
        error_msg = "Rapidata API Error"
        if status_code:
            error_msg += f" ({status_code})"
        if message:
            error_msg += f": {message}"

        super().__init__(error_msg)

    @staticmethod
    def _trace_id_from_details(details: Any) -> str | None:
        """Read the `traceId` ProblemDetails member, when the body carried one."""
        if isinstance(details, dict):
            raw = details.get("traceId")
            if isinstance(raw, str) and raw:
                return raw
        return None

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

        if self.details and isinstance(self.details, dict):
            title = self.details.get("title")
            errors = self.details.get("errors")

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

        if self.trace_id:
            error_parts.append(f"Trace Id: {self.trace_id}")
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
