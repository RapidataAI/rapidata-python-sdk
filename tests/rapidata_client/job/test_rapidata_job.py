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
from rapidata.api_client.models.review_reason_model import ReviewReasonModel
from rapidata.rapidata_client.job.rapidata_job import RapidataJob


def _job_get(state: str, review_reason: ReviewReasonModel | None = None) -> MagicMock:
    """A stand-in for the job GET response with just the fields the code reads."""
    job = MagicMock()
    job.state = AudienceJobState(state)
    job.review_reason = review_reason
    job.failure_message = None
    return job


def _make_job(job_get: MagicMock) -> tuple[RapidataJob, MagicMock]:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    openapi_service.order.job_api.job_job_id_get.return_value = job_get
    job = RapidataJob(
        job_id="job-1",
        name="My Job",
        audience_id="aud-1",
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
