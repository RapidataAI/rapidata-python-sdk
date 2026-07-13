"""Tests for surfacing job review/spend-limited states and the create cost warning.

Covers workstream E of the "cost warning + transparent review outcomes" work:
``RapidataJob`` must stop hanging on ``ManualApproval``/``SpendLimited`` and raise an
informative error instead, and ``assign_job`` must surface the create response's
optional ``costWarning`` as a Python warning without otherwise changing behavior.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.audience_job_state import AudienceJobState
from rapidata.api_client.models.create_job_endpoint_cost_warning_model import (
    CreateJobEndpointCostWarningModel,
)
from rapidata.api_client.models.review_reason_model import ReviewReasonModel
from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase
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


def test_display_progress_bar_raises_on_spend_limited():
    job, _ = _make_job(_job_get("SpendLimited"))

    with pytest.raises(Exception) as excinfo:
        job.display_progress_bar()

    assert "spend-limited" in str(excinfo.value).lower()


def _make_audience() -> tuple[RapidataAudienceBase, MagicMock]:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    audience = RapidataAudienceBase(
        id="aud-1", name="Aud", filters=[], openapi_service=openapi_service
    )
    return audience, openapi_service


def test_assign_job_warns_on_cost_warning():
    audience, openapi_service = _make_audience()
    response = MagicMock()
    response.job_id = "job-1"
    response.cost_warning = CreateJobEndpointCostWarningModel(
        estimatedCost=120.0, availableBalance=50.0, shortfall=70.0
    )
    openapi_service.order.job_api.job_post.return_value = response

    with pytest.warns(UserWarning) as record:
        audience.assign_job(MagicMock(id="def-1", name="My Job"))

    message = str(record[0].message)
    assert "120.00" in message
    assert "50.00" in message
    assert "70.00" in message
    assert "estimate" in message.lower()


def test_assign_job_no_warning_when_cost_within_balance():
    audience, openapi_service = _make_audience()
    response = MagicMock()
    response.job_id = "job-1"
    response.cost_warning = None
    openapi_service.order.job_api.job_post.return_value = response

    import warnings as _warnings

    with _warnings.catch_warnings():
        _warnings.simplefilter("error")
        job = audience.assign_job(MagicMock(id="def-1", name="My Job"))

    assert job.id == "job-1"
