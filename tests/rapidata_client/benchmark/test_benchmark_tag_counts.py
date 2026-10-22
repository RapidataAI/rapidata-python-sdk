"""Tests for listing a benchmark's tags with the number of prompts carrying each."""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.api_client.models.query_tags_by_benchmark_endpoint_output import (
    QueryTagsByBenchmarkEndpointOutput,
)
from rapidata.api_client.models.tag_summary import TagSummary
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark


def _make_benchmark(tags: list[TagSummary]) -> tuple[RapidataBenchmark, MagicMock]:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    svc.leaderboard.benchmark_api.benchmark_benchmark_id_tags_get.return_value = (
        QueryTagsByBenchmarkEndpointOutput(tags=tags)
    )
    return RapidataBenchmark("bm", "bm-1", svc), svc


def test_get_tag_counts_returns_one_row_per_tag():
    benchmark, svc = _make_benchmark(
        [
            TagSummary(value="Text", category="Capability", promptCount=24),
            TagSummary(value="outdoor", category=None, promptCount=3),
        ]
    )

    counts = benchmark.get_tag_counts()

    svc.leaderboard.benchmark_api.benchmark_benchmark_id_tags_get.assert_called_once_with(
        benchmark_id="bm-1"
    )
    assert counts.to_dict("records") == [
        {"value": "Text", "category": "Capability", "prompt_count": 24},
        {"value": "outdoor", "category": None, "prompt_count": 3},
    ]


def test_get_tag_counts_keeps_its_columns_when_the_benchmark_has_no_tags():
    benchmark, _ = _make_benchmark([])

    counts = benchmark.get_tag_counts()

    assert counts.empty
    assert list(counts.columns) == ["value", "category", "prompt_count"]
