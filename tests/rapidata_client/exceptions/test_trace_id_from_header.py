"""Tests for recovering the backend trace id when the error body has none.

A Kestrel request-timeout (408) or an LB-generated error is produced before any
handler runs, so it carries no problem+json body — but it still carries the
`x-trace-id` response header. Without the header fallback these errors print
"Trace Id: N/A" and support has nothing to correlate against.
"""

from __future__ import annotations

from rapidata.rapidata_client.api.rapidata_api_client import _trace_id_from_headers
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError


def test_header_trace_id_used_when_body_has_none():
    error = RapidataError(
        status_code=408, message="Request Timeout", trace_id="00-hdr-01"
    )

    assert error.trace_id == "00-hdr-01"
    assert "Trace Id: 00-hdr-01" in str(error)


def test_body_trace_id_wins_over_header():
    error = RapidataError(
        status_code=400,
        message="Bad request",
        details={"title": "Bad request", "traceId": "00-body-01"},
        trace_id="00-hdr-01",
    )

    assert error.trace_id == "00-body-01"


def test_no_trace_id_anywhere_still_reports_na():
    error = RapidataError(status_code=500, message="Boom")

    assert error.trace_id is None
    assert "Trace Id: N/A" in str(error)


def test_failed_upload_picks_up_header_trace_id():
    error = RapidataError(
        status_code=408, message="Request Timeout", trace_id="00-hdr-01"
    )

    failed = FailedUpload.from_exception("./a.jpg", error)

    assert failed.trace_id == "00-hdr-01"


def test_trace_id_from_headers_is_case_insensitive():
    assert _trace_id_from_headers({"X-Trace-Id": "00-abc-01"}) == "00-abc-01"
    assert _trace_id_from_headers({"x-trace-id": "00-abc-01"}) == "00-abc-01"


def test_trace_id_from_headers_tolerates_missing_or_odd_input():
    assert _trace_id_from_headers(None) is None
    assert _trace_id_from_headers({}) is None
    assert _trace_id_from_headers({"x-trace-id": ""}) is None
    assert _trace_id_from_headers("not-a-mapping") is None
