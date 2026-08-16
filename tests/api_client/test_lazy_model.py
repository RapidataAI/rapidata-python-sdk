"""Tests for LazyValidatedModel's handling of backend schema drift.

The contract under test: drift the caller never reads is absorbed silently — the
model still constructs and the span carries an event, not an error status. Only
reading a drifted field is a failure.
"""

from __future__ import annotations

from typing import Optional

import pytest
from pydantic import Field, StrictInt, StrictStr, ValidationError

import rapidata.api_client.lazy_model as lazy_model_module
from rapidata.api_client.lazy_model import LazyValidatedModel


class _Audience(LazyValidatedModel):
    id: StrictStr
    graduation_score: float = Field(alias="graduationScore")


class _Variant(LazyValidatedModel):
    t: Optional[StrictStr] = Field(default=None, alias="_t")
    size: StrictInt


def _construct(cls, data: dict):
    """Mimic the generated from_dict path: validate, fall back to lazy construct."""
    try:
        return cls.model_validate(data)
    except ValidationError as error:
        return cls._lazy_construct(data, error)


@pytest.fixture
def recorded_drift(monkeypatch):
    calls: list[tuple[str, list[str]]] = []

    class _Tracer:
        def record_schema_drift(self, model_name: str, fields: list[str]) -> None:
            calls.append((model_name, fields))

    monkeypatch.setattr(lazy_model_module, "tracer", _Tracer())
    return calls


def test_missing_field_does_not_fail_the_span(recorded_drift):
    model = _construct(_Audience, {"id": "aud-1"})

    assert model.id == "aud-1"
    assert recorded_drift == [("_Audience", ["graduation_score"])]


def test_reading_a_drifted_field_raises(recorded_drift):
    model = _construct(_Audience, {"id": "aud-1"})

    with pytest.raises(TypeError, match="graduation_score"):
        _ = model.graduation_score


def test_clean_payload_records_nothing(recorded_drift):
    model = _construct(_Audience, {"id": "aud-1", "graduationScore": 0.5})

    assert model.graduation_score == 0.5
    assert recorded_drift == []


def test_discriminator_drift_still_raises(recorded_drift):
    # A bad `_t` means oneOf/anyOf picked the wrong variant — a structural failure
    # that lazy validation must not absorb.
    with pytest.raises(ValidationError):
        _construct(_Variant, {"_t": 7, "size": 1})

    assert recorded_drift == []
