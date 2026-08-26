"""Tests for the ranking pair-maker selection and budget handling.

Small rankings (<= 10 items) use the full-permutation pair maker, which takes
no budget of its own — the comparison budget must be honored by scaling the
per-pair response requirement instead of being silently dropped.
"""

from __future__ import annotations

import pytest

from rapidata.rapidata_client.workflow._multi_ranking_workflow import (
    FULL_PERMUTATION_GROUP_SIZE_THRESHOLD,
    MultiRankingWorkflow,
)


def _make(max_group_size: int, budget: int, responses_per_comparison: int = 1):
    return MultiRankingWorkflow(
        instruction="Which one is better?",
        comparison_budget_per_ranking=budget,
        random_comparisons_ratio=0.5,
        max_group_size=max_group_size,
        responses_per_comparison=responses_per_comparison,
    )


def test_small_ranking_spreads_budget_over_all_pairs():
    # 7 items -> 21 unique pairs; a budget of 5000 must not collapse to 21.
    workflow = _make(max_group_size=7, budget=5000)

    assert (
        workflow.pair_maker_config.actual_instance.t == "FullPermutationPairMaker"
    )
    assert workflow.responses_per_datapoint == 5000 // 21  # 238 -> 4998 total


def test_small_ranking_budget_multiplies_responses_per_comparison():
    workflow = _make(max_group_size=7, budget=100, responses_per_comparison=3)

    assert workflow.responses_per_datapoint == (100 // 21) * 3


def test_budget_below_pair_count_keeps_full_coverage_and_warns(caplog):
    # 10 items -> 45 pairs; every pair still needs at least one comparison.
    with caplog.at_level("WARNING", logger="rapidata"):
        workflow = _make(max_group_size=10, budget=20, responses_per_comparison=2)

    assert workflow.responses_per_datapoint == 2
    assert any("budget" in r.getMessage().lower() for r in caplog.records)


def test_large_ranking_uses_online_pair_maker_with_budget():
    workflow = _make(
        max_group_size=FULL_PERMUTATION_GROUP_SIZE_THRESHOLD + 1,
        budget=5000,
        responses_per_comparison=2,
    )

    online = workflow.pair_maker_config.actual_instance
    assert online.t == "OnlinePairMaker"
    assert online.total_comparison_budget == 5000
    assert online.random_matches_ratio == pytest.approx(0.5)
    assert workflow.responses_per_datapoint == 2
