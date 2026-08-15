"""Tests for how lazy validation reports backend/SDK schema drift to telemetry.

Absorbed drift used to fail the enclosing span. That reported an outage that had
not happened: the model is still constructed and the caller still gets its result,
so the only client that a removed field actually breaks is one that reads it. A
single customer on a stale SDK polling one endpoint was enough to make absorbed
drift outnumber every genuine platform error, which is what these tests pin down —
drift is an event, an access-time failure is an error.
"""

from __future__ import annotations

from typing import Optional

import pytest
from pydantic import Field, ValidationError

from rapidata.api_client.lazy_model import LazyValidatedModel


class _Audience(LazyValidatedModel):
    id: str
    graduation_score: float = Field(alias="graduationScore")


class _RecordingSpan:
    """Minimal stand-in for an OTel span that records what it was told."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []
        self.status: Optional[str] = None

    def is_recording(self) -> bool:
        return True

    def add_event(self, name: str, attributes: Optional[dict] = None) -> None:
        self.events.append((name, attributes or {}))

    def set_status(self, status) -> None:
        self.status = str(status)


def _construct_with_drift() -> _Audience:
    """Build the model from a payload missing the field the SDK still requires."""
    try:
        return _Audience.model_validate({"id": "aud_1"})
    except ValidationError as error:
        return _Audience._lazy_construct({"id": "aud_1"}, error)


@pytest.fixture
def recording_span(monkeypatch) -> _RecordingSpan:
    span = _RecordingSpan()
    # The tracer resolves get_current_span off the opentelemetry.trace module at
    # call time; patching the module attribute is what reaches it, since
    # `rapidata.rapidata_client.config.tracer` is the exported tracer instance
    # rather than the submodule of the same name.
    monkeypatch.setattr("opentelemetry.trace.get_current_span", lambda: span)
    return span


class TestAbsorbedDrift:
    def test_drift_is_recorded_as_an_event(self, recording_span):
        _construct_with_drift()

        assert [name for name, _ in recording_span.events] == ["api.schema_drift"]
        attributes = recording_span.events[0][1]
        assert attributes["api.schema_drift.model"] == "_Audience"
        assert attributes["api.schema_drift.fields"] == ["graduation_score"]

    def test_drift_does_not_fail_the_span(self, recording_span):
        _construct_with_drift()

        assert recording_span.status is None

    def test_unaffected_fields_stay_readable(self, recording_span):
        assert _construct_with_drift().id == "aud_1"


class TestAccessTimeFailure:
    def test_reading_the_drifted_field_still_raises(self, recording_span):
        model = _construct_with_drift()

        with pytest.raises(TypeError, match="graduation_score"):
            _ = model.graduation_score
