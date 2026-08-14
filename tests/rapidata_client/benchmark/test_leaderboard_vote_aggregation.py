"""Tests for the leaderboard's vote aggregation.

``vote_aggregation`` decides whether the responses on one matchup collapse to a
single majority win or each count as their own matchup. Unlike the prompt-tag
filters it is settable after creation, because standings are derived from the raw
responses on every read.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.vote_aggregation import (
    VoteAggregation as VoteAggregationModel,
)
from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
    RapidataLeaderboard,
)
from rapidata.rapidata_client.benchmark.leaderboard.vote_aggregation import (
    VoteAggregation,
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
    create.return_value.vote_aggregation = VoteAggregationModel.MAJORITYVOTE
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


def _patched_payload(leaderboard: RapidataLeaderboard):
    patch = (
        leaderboard._RapidataLeaderboard__openapi_service.leaderboard.leaderboard_api.leaderboard_leaderboard_id_patch  # type: ignore[attr-defined]
    )
    return patch.call_args.kwargs["update_leaderboard_endpoint_input"]


def test_create_leaderboard_defaults_to_majority_vote() -> None:
    benchmark = _make_benchmark()
    leaderboard = benchmark.create_leaderboard(
        name="lb", instruction="Which is better?"
    )

    assert (
        _sent_payload(benchmark).vote_aggregation == VoteAggregationModel.MAJORITYVOTE
    )
    assert leaderboard.vote_aggregation is VoteAggregation.MAJORITY_VOTE


def test_create_leaderboard_threads_all_votes_to_the_wire() -> None:
    benchmark = _make_benchmark()
    create = benchmark._openapi_service.leaderboard.leaderboard_api.leaderboard_post
    create.return_value.vote_aggregation = VoteAggregationModel.ALLVOTES

    leaderboard = benchmark.create_leaderboard(
        name="lb",
        instruction="Which is better?",
        vote_aggregation=VoteAggregation.ALL_VOTES,
    )

    assert _sent_payload(benchmark).vote_aggregation == VoteAggregationModel.ALLVOTES
    assert leaderboard.vote_aggregation is VoteAggregation.ALL_VOTES


def test_setter_patches_the_new_aggregation() -> None:
    leaderboard = _make_leaderboard()

    leaderboard.vote_aggregation = VoteAggregation.ALL_VOTES

    assert leaderboard.vote_aggregation is VoteAggregation.ALL_VOTES
    assert _patched_payload(leaderboard).vote_aggregation == (
        VoteAggregationModel.ALLVOTES
    )


def test_unrelated_setters_preserve_the_aggregation() -> None:
    """A patch that omits the field would be a no-op, but sending a stale value
    would silently un-binarize the board."""
    leaderboard = _make_leaderboard(vote_aggregation=VoteAggregation.ALL_VOTES)

    leaderboard.min_responses_per_matchup = 5

    assert _patched_payload(leaderboard).vote_aggregation == (
        VoteAggregationModel.ALLVOTES
    )


def test_unresolved_aggregation_is_fetched_once_on_read() -> None:
    """The benchmark's leaderboard listing omits the field, so a listed leaderboard
    has to resolve it rather than assume the default."""
    leaderboard = _make_leaderboard()
    api = leaderboard._RapidataLeaderboard__openapi_service.leaderboard.leaderboard_api  # type: ignore[attr-defined]
    api.leaderboard_leaderboard_id_get.return_value.vote_aggregation = (
        VoteAggregationModel.ALLVOTES
    )

    assert leaderboard.vote_aggregation is VoteAggregation.ALL_VOTES
    assert leaderboard.vote_aggregation is VoteAggregation.ALL_VOTES
    api.leaderboard_leaderboard_id_get.assert_called_once_with(leaderboard_id="lb-1")


def test_unrelated_setters_leave_an_unresolved_aggregation_alone() -> None:
    """Sending a guessed value here would silently rewrite the board's setting."""
    leaderboard = _make_leaderboard()

    leaderboard.min_responses_per_matchup = 5

    assert _patched_payload(leaderboard).vote_aggregation is None


@pytest.mark.parametrize("value", ["MajorityVote", 1, None])
def test_setter_rejects_non_enum_values(value: object) -> None:
    leaderboard = _make_leaderboard()

    with pytest.raises(ValueError):
        leaderboard.vote_aggregation = value  # type: ignore[assignment]


def test_round_trips_through_the_backend_model() -> None:
    for member in VoteAggregation:
        assert VoteAggregation._from_backend_model(member._to_backend_model()) is member
