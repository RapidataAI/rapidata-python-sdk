"""Tests for the audience_will_never_produce_responses verdict.

The verdict tells a stuck audience (recruiting never started, or marked ready with
an empty pool) apart from one that is merely early in recruiting — the latter must
NOT be judged stuck, or a blocking get_results() would raise on a healthy audience
that just needs time. Curated audiences (no funnel of their own) are never stuck.
"""

from __future__ import annotations

from rapidata.api_client.models.audience_status import AudienceStatus
from rapidata.rapidata_client.audience.recruiting import (
    RecruitingMetrics,
    audience_will_never_produce_responses,
)


def _metrics(graduated=0, distilling=0, dropped=0, inactive=0) -> RecruitingMetrics:
    return RecruitingMetrics(
        graduated=graduated, distilling=distilling, dropped=dropped, inactive=inactive
    )


def test_graduated_annotators_can_answer():
    m = _metrics(graduated=4)
    assert not audience_will_never_produce_responses(AudienceStatus.READY, m)


def test_distilling_is_filling_up_not_stuck():
    m = _metrics(distilling=6)
    assert not audience_will_never_produce_responses(AudienceStatus.RECRUITING, m)


def test_created_never_recruited_is_stuck():
    # Never-recruited audience has no funnel of its own.
    assert audience_will_never_produce_responses(AudienceStatus.CREATED, None)


def test_early_recruiting_with_empty_funnel_is_not_stuck():
    # Recruiting has started but nobody has entered the funnel yet — give it time.
    assert not audience_will_never_produce_responses(AudienceStatus.PENDING, None)
    assert not audience_will_never_produce_responses(AudienceStatus.RECRUITING, None)


def test_curated_audience_is_not_stuck():
    # Curated audiences report no funnel (None) and draw on their own ready pool.
    assert not audience_will_never_produce_responses(AudienceStatus.READY, None)


def test_ready_but_empty_pool_is_stuck():
    # Marked ready, yet the funnel confirms nobody graduated or is distilling.
    m = _metrics(dropped=3, inactive=1)
    assert audience_will_never_produce_responses(AudienceStatus.READY, m)
