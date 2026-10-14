"""Tests for RapidataJob surfacing states it can't progress out of on its own.

A job that enters ManualApproval, SpendLimited, Paused or Blocked never reaches Completed/Failed,
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


def test_get_results_raises_on_paused():
    job, _ = _make_job(_job_get("Paused"))

    with pytest.raises(Exception) as excinfo:
        job.get_results()

    message = str(excinfo.value)
    assert "paused" in message
    assert "resume()" in message


def test_get_results_raises_on_blocked_with_job_page():
    job, _ = _make_job(_job_get("Blocked"))

    with pytest.raises(Exception) as excinfo:
        job.get_results()

    message = str(excinfo.value)
    assert "blocked" in message
    assert "unflag" in message
    assert job.job_details_page in message


def test_display_progress_bar_raises_on_blocked():
    job, _ = _make_job(_job_get("Blocked"))

    with pytest.raises(Exception) as excinfo:
        job.display_progress_bar()

    assert "blocked" in str(excinfo.value)


def test_pause_and_resume_call_endpoints_and_chain():
    job, openapi_service = _make_job(_job_get("Running"))

    assert job.pause() is job
    openapi_service.order.job_api.job_job_id_pause_post.assert_called_once_with("job-1")

    assert job.resume() is job
    openapi_service.order.job_api.job_job_id_resume_post.assert_called_once_with(
        "job-1"
    )


def test_get_results_preliminary_returns_snapshot_while_running():
    job_get = _job_get("Running")
    job_get.pipeline_id = "pip-1"
    job, openapi_service = _make_job(job_get)
    pipeline_api = openapi_service.pipeline.pipeline_api
    pipeline_api.pipeline_pipeline_id_preliminary_download_post.return_value.download_id = (
        "dl-1"
    )
    response = (
        pipeline_api.pipeline_preliminary_download_preliminary_download_id_get_with_http_info.return_value
    )
    response.status_code = 200
    response.raw_data = json.dumps({"info": {}, "results": [1]}).encode()

    results = job.get_results(preliminary_results=True)

    assert results == {"info": {}, "results": [1]}
    assert (
        pipeline_api.pipeline_pipeline_id_preliminary_download_post.call_args.args[0]
        == "pip-1"
    )
    pipeline_api.pipeline_preliminary_download_preliminary_download_id_get_with_http_info.assert_called_once_with(
        preliminary_download_id="dl-1"
    )
    openapi_service.order.job_api.job_job_id_download_results_get.assert_not_called()


def test_get_results_preliminary_returns_final_results_when_completed():
    job, openapi_service = _make_job(_job_get("Completed"))
    openapi_service.order.job_api.job_job_id_download_results_get.return_value = (
        json.dumps({"info": {}, "results": []})
    )

    job.get_results(preliminary_results=True)

    openapi_service.pipeline.pipeline_api.pipeline_pipeline_id_preliminary_download_post.assert_not_called()
