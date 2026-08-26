"""Tests for RapidataLeaderboard.update().

The leaderboard's mutable configuration is changed through this one method rather
than through per-field property setters, so the patch it sends must carry exactly
the fields the caller named and nothing else.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
    RapidataLeaderboard,
)


def _make_leaderboard(**kwargs) -> RapidataLeaderboard:
    return RapidataLeaderboard(
        "lb",
        "Which is better?",
        False,
        False,
        False,
        2000,
        3,
        "bm-1",
        "lb-1",
        MagicMock(),
        **kwargs,
    )


def _patched_payload(leaderboard: RapidataLeaderboard):
    patch = leaderboard._RapidataLeaderboard__openapi_service.leaderboard.leaderboard_api.leaderboard_leaderboard_id_patch  # type: ignore[attr-defined]
    return patch.call_args.kwargs["update_leaderboard_endpoint_input"]


def test_update_sends_only_the_named_fields() -> None:
    leaderboard = _make_leaderboard()

    leaderboard.update(name="renamed")

    payload = _patched_payload(leaderboard)
    assert payload.name == "renamed"
    assert payload.response_budget is None
    assert payload.min_responses is None
    assert leaderboard.name == "renamed"


def test_update_resolves_a_named_level_of_detail() -> None:
    leaderboard = _make_leaderboard()

    leaderboard.update(level_of_detail="high")

    assert _patched_payload(leaderboard).response_budget == 8000
    assert leaderboard.response_budget == 8000
    assert leaderboard.level_of_detail == "high"


def test_update_accepts_a_custom_budget() -> None:
    leaderboard = _make_leaderboard()

    leaderboard.update(level_of_detail=5000)

    assert _patched_payload(leaderboard).response_budget == 5000
    assert leaderboard.level_of_detail == "custom"


def test_update_changes_several_fields_in_one_request() -> None:
    leaderboard = _make_leaderboard()
    patch = leaderboard._RapidataLeaderboard__openapi_service.leaderboard.leaderboard_api.leaderboard_leaderboard_id_patch  # type: ignore[attr-defined]

    leaderboard.update(name="renamed", min_responses_per_matchup=5)

    patch.assert_called_once()
    payload = _patched_payload(leaderboard)
    assert payload.name == "renamed"
    assert payload.min_responses == 5


@pytest.mark.parametrize("min_responses", [2, 0, -1, True, 3.5, "5"])
def test_update_rejects_invalid_min_responses(min_responses: object) -> None:
    leaderboard = _make_leaderboard()

    with pytest.raises(ValueError):
        leaderboard.update(min_responses_per_matchup=min_responses)  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["", 5])
def test_update_rejects_invalid_names(name: object) -> None:
    leaderboard = _make_leaderboard()

    with pytest.raises(ValueError):
        leaderboard.update(name=name)  # type: ignore[arg-type]


@pytest.mark.parametrize("level_of_detail", ["enormous", 0, -5, True])
def test_update_rejects_invalid_levels_of_detail(level_of_detail: object) -> None:
    leaderboard = _make_leaderboard()

    with pytest.raises(ValueError):
        leaderboard.update(level_of_detail=level_of_detail)  # type: ignore[arg-type]


def test_update_with_no_arguments_sends_an_empty_patch() -> None:
    """A no-op call must not resend the current state as if it were a change."""
    leaderboard = _make_leaderboard()

    leaderboard.update()

    payload = _patched_payload(leaderboard)
    assert payload.name is None
    assert payload.response_budget is None
    assert payload.min_responses is None
    assert payload.vote_aggregation is None


@pytest.mark.parametrize(
    "attribute",
    ["name", "level_of_detail", "min_responses_per_matchup", "response_budget"],
)
def test_configuration_properties_are_read_only(attribute: str) -> None:
    leaderboard = _make_leaderboard()

    with pytest.raises(AttributeError):
        setattr(leaderboard, attribute, "whatever")
