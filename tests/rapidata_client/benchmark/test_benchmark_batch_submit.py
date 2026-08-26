"""Tests for ``RapidataBenchmark.run`` submitting participants in batches.

``run`` sends every ``CREATED`` participant to the batch submit endpoint in one
request (chunked to the endpoint's 100-id cap) rather than one request per
participant, so the batch is evaluated symmetrically as a single run.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.api_client.models.participant_status import ParticipantStatus
from rapidata.rapidata_client.benchmark.participant.participant import (
    BenchmarkParticipant,
)
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark


def _make_benchmark(
    statuses: list[ParticipantStatus],
) -> tuple[RapidataBenchmark, list[BenchmarkParticipant]]:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    benchmark = RapidataBenchmark("bm", "bm-1", svc)

    participants = [
        BenchmarkParticipant(
            name=f"model-{i}",
            id=f"p-{i}",
            openapi_service=svc,
            benchmark_id="bm-1",
            status=status,
        )
        for i, status in enumerate(statuses)
    ]
    # Seed the participants cache so `run` does not hit the (mocked) list endpoint.
    setattr(benchmark, "_RapidataBenchmark__participants", participants)
    return benchmark, participants


def _submit_calls(benchmark: RapidataBenchmark):
    return benchmark._openapi_service.leaderboard.participant_api.participants_submit_post.call_args_list


def test_run_submits_created_participants_in_a_single_batch() -> None:
    benchmark, participants = _make_benchmark([ParticipantStatus.CREATED] * 3)

    benchmark.run()

    calls = _submit_calls(benchmark)
    assert len(calls) == 1
    payload = calls[0].kwargs["submit_participants_endpoint_input"]
    assert payload.participant_ids == ["p-0", "p-1", "p-2"]
    assert all(p.status == ParticipantStatus.SUBMITTED for p in participants)


def test_run_only_submits_created_participants() -> None:
    benchmark, participants = _make_benchmark(
        [
            ParticipantStatus.CREATED,
            ParticipantStatus.SUBMITTED,
            ParticipantStatus.CREATED,
        ]
    )

    benchmark.run()

    calls = _submit_calls(benchmark)
    assert len(calls) == 1
    payload = calls[0].kwargs["submit_participants_endpoint_input"]
    assert payload.participant_ids == ["p-0", "p-2"]


def test_run_chunks_at_the_hundred_id_cap() -> None:
    benchmark, _ = _make_benchmark([ParticipantStatus.CREATED] * 150)

    benchmark.run()

    calls = _submit_calls(benchmark)
    assert len(calls) == 2
    first = calls[0].kwargs["submit_participants_endpoint_input"].participant_ids
    second = calls[1].kwargs["submit_participants_endpoint_input"].participant_ids
    assert len(first) == 100
    assert len(second) == 50


def test_run_with_no_created_participants_sends_nothing() -> None:
    benchmark, _ = _make_benchmark([ParticipantStatus.SUBMITTED])

    benchmark.run()

    assert _submit_calls(benchmark) == []
