"""Tests for the leaderboard prompt-tag filters.

``included_tags`` / ``excluded_tags`` restrict which of a benchmark's prompts a
leaderboard collects matchups for. They are create-only by design: set on
``create_leaderboard``, read back as properties, never mutated.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
    RapidataLeaderboard,
)
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark


def _make_benchmark() -> RapidataBenchmark:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    create = svc.leaderboard.leaderboard_api.leaderboard_post
    create.return_value.benchmark_id = "bm-1"
    create.return_value.id = "lb-1"
    create.return_value.response_budget = 2000
    create.return_value.min_responses = 3
    return RapidataBenchmark("bm", "bm-1", svc)


def _sent_payload(benchmark: RapidataBenchmark):
    create = benchmark._openapi_service.leaderboard.leaderboard_api.leaderboard_post
    return create.call_args.kwargs["create_leaderboard_endpoint_input"]


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


def test_create_leaderboard_threads_tags_to_the_wire() -> None:
    benchmark = _make_benchmark()
    leaderboard = benchmark.create_leaderboard(
        name="lb",
        instruction="Which is better?",
        included_tags=["outdoor"],
        excluded_tags=["nsfw"],
    )

    payload = _sent_payload(benchmark)
    assert payload.included_tags == ["outdoor"]
    assert payload.excluded_tags == ["nsfw"]
    # The create response does not echo the tags, so the returned entity has to
    # carry the values the caller passed.
    assert leaderboard.included_tags == ["outdoor"]
    assert leaderboard.excluded_tags == ["nsfw"]


def test_create_leaderboard_omits_tags_by_default() -> None:
    benchmark = _make_benchmark()
    leaderboard = benchmark.create_leaderboard(
        name="lb", instruction="Which is better?"
    )

    payload = _sent_payload(benchmark)
    assert payload.included_tags is None
    assert payload.excluded_tags is None
    # Unrestricted reads back as empty, matching the wire contract's "empty means
    # no restriction".
    assert leaderboard.included_tags == []
    assert leaderboard.excluded_tags == []


def test_tags_default_to_empty_lists() -> None:
    leaderboard = _make_leaderboard()
    assert leaderboard.included_tags == []
    assert leaderboard.excluded_tags == []


def test_tag_properties_do_not_expose_internal_state() -> None:
    """Mutating the returned list must not re-scope the leaderboard."""
    included = ["outdoor"]
    leaderboard = _make_leaderboard(included_tags=included)

    leaderboard.included_tags.append("indoor")
    included.append("city")

    assert leaderboard.included_tags == ["outdoor"]


@pytest.mark.parametrize("attribute", ["included_tags", "excluded_tags"])
def test_tags_are_read_only(attribute: str) -> None:
    """Create-only by design: a leaderboard is never re-scoped in place."""
    leaderboard = _make_leaderboard(included_tags=["outdoor"], excluded_tags=["nsfw"])

    with pytest.raises(AttributeError):
        setattr(leaderboard, attribute, ["something-else"])
