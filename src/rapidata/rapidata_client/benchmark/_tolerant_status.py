"""Unknown ``ParticipantStatus`` / ``StandingStatus`` strings parse as pseudo-members carrying
the raw value, so a status the server adds later doesn't break standings and participant reads.
"""

from __future__ import annotations

from enum import Enum

from rapidata.api_client.models.participant_status import ParticipantStatus
from rapidata.api_client.models.standing_status import StandingStatus


def _missing_(cls: type[Enum], value: object) -> Enum | None:
    if not isinstance(value, str):
        return None
    member = str.__new__(cls, value)  # type: ignore[call-overload]
    member._name_ = value.upper()
    member._value_ = value
    return cls._value2member_map_.setdefault(value, member)


def make_tolerant(*enums: type[Enum]) -> None:
    """Install the fallback; pydantic reads it only when it builds a model's schema."""
    for enum in enums:
        setattr(enum, "_missing_", classmethod(_missing_))


make_tolerant(ParticipantStatus, StandingStatus)
