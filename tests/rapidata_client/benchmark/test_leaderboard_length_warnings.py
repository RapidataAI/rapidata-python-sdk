from __future__ import annotations

import logging
from unittest.mock import MagicMock, PropertyMock, patch

from rapidata.api_client.models.vote_aggregation import (
    VoteAggregation as VoteAggregationModel,
)
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark

LONG_PROMPT = "a" * 325


def _make_benchmark() -> RapidataBenchmark:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    create = svc.leaderboard.leaderboard_api.leaderboard_post
    create.return_value.benchmark_id = "bm-1"
    create.return_value.id = "lb-1"
    create.return_value.response_budget = 2000
    create.return_value.min_responses = 5
    create.return_value.vote_aggregation = VoteAggregationModel.MAJORITYVOTE
    return RapidataBenchmark("bm", "bm-1", svc)


def _warnings(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def _create(benchmark: RapidataBenchmark, prompts, **kwargs) -> None:
    with patch.object(
        RapidataBenchmark, "prompts", new_callable=PropertyMock, return_value=prompts
    ):
        benchmark.create_leaderboard(name="lb", **kwargs)


def test_long_instruction_warns(caplog):
    with caplog.at_level(logging.WARNING):
        _create(
            _make_benchmark(),
            ["short"],
            instruction="Which video has better audio: clear speech, sound that fits the scene, and no noise?",
        )

    assert any("keep it under 80" in m for m in _warnings(caplog))


def test_long_prompts_warn_only_when_shown(caplog):
    with caplog.at_level(logging.WARNING):
        _create(
            _make_benchmark(), [LONG_PROMPT, "short"], instruction="Which is better?"
        )
    assert _warnings(caplog) == []

    with caplog.at_level(logging.WARNING):
        _create(
            _make_benchmark(),
            [LONG_PROMPT, "short", None],
            instruction="Which is better?",
            show_prompt=True,
        )
    [message] = _warnings(caplog)
    assert (
        "1 of 2 benchmark prompt(s) are longer than 150 characters (longest: 325)"
        in message
    )
    assert "shorter prompts (under 150 characters) give better results" in message


def test_prompt_check_failure_does_not_block_creation(caplog):
    benchmark = _make_benchmark()
    with (
        caplog.at_level(logging.WARNING),
        patch.object(
            RapidataBenchmark,
            "prompts",
            new_callable=PropertyMock,
            side_effect=RuntimeError("boom"),
        ),
    ):
        benchmark.create_leaderboard(
            name="lb", instruction="Which is better?", show_prompt=True
        )

    assert _warnings(caplog) == []
    benchmark._openapi_service.leaderboard.leaderboard_api.leaderboard_post.assert_called_once()
