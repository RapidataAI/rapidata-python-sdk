"""Tests for RapidataJob surfacing states it can't progress out of on its own.

A job that enters ManualApproval or SpendLimited never reaches Completed/Failed,
so waiting on it (e.g. via get_results) must raise an informative error instead
of blocking the caller forever.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.audience_job_state import AudienceJobState
from rapidata.api_client.models.audience_status import AudienceStatus
from rapidata.api_client.models.review_reason_model import ReviewReasonModel
from rapidata.rapidata_client.job.rapidata_job import RapidataJob


def _job_get(state: str, review_reason: ReviewReasonModel | None = None) -> MagicMock:
    """A stand-in for the job GET response with just the fields the code reads."""
    job = MagicMock()
    job.state = AudienceJobState(state)
    job.review_reason = review_reason
    job.failure_message = None
    return job


def _make_job(
    job_get: MagicMock,
    audience_status: AudienceStatus = AudienceStatus.READY,
    users_per_state: dict[str, int] | None = None,
    audience_id: str = "aud-1",
) -> tuple[RapidataJob, MagicMock]:
    # Default to a healthy pool with graduated annotators so the readiness check is a
    # no-op unless a test opts into an empty/stuck funnel.
    if users_per_state is None:
        users_per_state = {"Graduated": 5}
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    openapi_service.order.job_api.job_job_id_get.return_value = job_get
    audience = MagicMock()
    audience.name = "My Audience"
    audience.status = audience_status
    openapi_service.audience.audience_api.audience_audience_id_get.return_value = (
        audience
    )
    openapi_service.audience.audience_api.audience_audience_id_user_metrics_get.return_value.users_per_state = (
        users_per_state
    )
    job = RapidataJob(
        job_id="job-1",
        name="My Job",
        audience_id=audience_id,
        created_at=MagicMock(),
        definition_id="def-1",
        openapi_service=openapi_service,
    )
    return job, openapi_service


def test_get_results_raises_on_manual_approval_with_reason():
    job, _ = _make_job(
        _job_get("ManualApproval", review_reason=ReviewReasonModel.CONTENTFLAGGED)
    )

    with pytest.raises(Exception) as excinfo:
        job.get_results()

    message = str(excinfo.value)
    assert "being reviewed" in message
    assert "ContentFlagged" in message


def test_get_results_raises_on_manual_approval_without_reason():
    job, _ = _make_job(_job_get("ManualApproval", review_reason=None))

    with pytest.raises(Exception) as excinfo:
        job.get_results()

    message = str(excinfo.value)
    assert "being reviewed" in message
    # A null reason must not leak into the message as empty parentheses.
    assert "()" not in message


def test_get_results_raises_on_spend_limited():
    job, _ = _make_job(_job_get("SpendLimited"))

    with pytest.raises(Exception) as excinfo:
        job.get_results()

    message = str(excinfo.value).lower()
    assert "spend-limited" in message
    assert "partial results" in message
    assert "top up" in message


def test_display_progress_bar_raises_on_spend_limited():
    job, _ = _make_job(_job_get("SpendLimited"))

    with pytest.raises(Exception) as excinfo:
        job.display_progress_bar()

    assert "spend-limited" in str(excinfo.value).lower()


def test_get_results_raises_when_recruiting_never_started():
    # Never-recruited audience: empty funnel, status Created.
    job, _ = _make_job(
        _job_get("Running"),
        audience_status=AudienceStatus.CREATED,
        users_per_state={},
    )

    with pytest.raises(Exception) as excinfo:
        job.get_results()

    message = str(excinfo.value)
    assert "can never produce responses" in message.lower()
    assert "start_recruiting()" in message
    assert "global" in message.lower()


def test_get_results_raises_when_pool_empty_but_marked_ready():
    # Marked ready, but the funnel shows nobody graduated or distilling.
    job, _ = _make_job(
        _job_get("Running"),
        audience_status=AudienceStatus.READY,
        users_per_state={"Dropped": 3, "Inactive": 1},
    )

    with pytest.raises(Exception) as excinfo:
        job.get_results()

    assert "can never produce responses" in str(excinfo.value).lower()


def test_display_progress_bar_raises_when_recruiting_never_started():
    job, _ = _make_job(
        _job_get("Running"),
        audience_status=AudienceStatus.CREATED,
        users_per_state={},
    )

    with pytest.raises(Exception) as excinfo:
        job.display_progress_bar()

    assert "can never produce responses" in str(excinfo.value).lower()


def test_get_results_skips_status_probe_when_annotators_graduated():
    # With graduated annotators the funnel already proves the job can be answered,
    # so there is no need to fetch the audience status.
    job, openapi_service = _make_job(
        _job_get("Completed"), users_per_state={"Graduated": 8}
    )
    openapi_service.order.job_api.job_job_id_download_results_get.return_value = (
        json.dumps({"info": {}, "results": []})
    )

    job.get_results()

    openapi_service.audience.audience_api.audience_audience_id_get.assert_not_called()


def test_get_results_happy_path_returns_results():
    job, openapi_service = _make_job(_job_get("Completed"))
    openapi_service.order.job_api.job_job_id_download_results_get.return_value = (
        json.dumps({"info": {}, "results": []})
    )

    results = job.get_results()

    assert results == {"info": {}, "results": []}
    openapi_service.order.job_api.job_job_id_download_results_get.assert_called_once_with(
        job_id="job-1"
    )
