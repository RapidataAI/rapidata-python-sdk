"""Tests for ``skip_initial_run`` on leaderboard creation.

The flag suppresses the initial run that evaluates the benchmark's existing
models against each other. It is create-only: the backend decides it at creation
time and does not record it on the leaderboard, so there is nothing to read back.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.api_client.models.vote_aggregation import (
    VoteAggregation as VoteAggregationModel,
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


def test_create_leaderboard_threads_skip_initial_run_to_the_wire() -> None:
    benchmark = _make_benchmark()
    benchmark.create_leaderboard(
        name="lb",
        instruction="Which is better?",
        skip_initial_run=True,
    )

    assert _sent_payload(benchmark).skip_initial_run is True


def test_create_leaderboard_runs_initially_by_default() -> None:
    benchmark = _make_benchmark()
    benchmark.create_leaderboard(
        name="lb",
        instruction="Which is better?",
    )

    # Explicitly False rather than omitted, so the request never relies on the
    # server-side default to keep today's behaviour.
    assert _sent_payload(benchmark).skip_initial_run is False
