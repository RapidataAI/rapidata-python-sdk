"""Tests for ``RapidataBenchmark.update``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark


def _make_benchmark() -> RapidataBenchmark:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    return RapidataBenchmark("bm", "bm-1", svc)


def test_update_patches_min_assets_per_prompt() -> None:
    benchmark = _make_benchmark()

    benchmark.update(min_assets_per_prompt=4)

    patch = (
        benchmark._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_patch
    )
    patch.assert_called_once()
    assert patch.call_args.kwargs["benchmark_id"] == "bm-1"
    payload = patch.call_args.kwargs["update_benchmark_endpoint_input"]
    assert payload.min_assets_per_prompt == 4


@pytest.mark.parametrize("value", [1, 0, -3, True])
def test_update_rejects_min_assets_below_two_or_non_int(value) -> None:
    benchmark = _make_benchmark()

    with pytest.raises(ValueError):
        benchmark.update(min_assets_per_prompt=value)

    benchmark._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_patch.assert_not_called()
