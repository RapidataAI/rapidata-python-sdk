"""Tests for the create-time cost warning surfaced by assign_job.

When job creation returns a costWarning (estimate exceeds balance), assign_job
logs an advisory warning. The job is created regardless; behaviour is otherwise
unchanged.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import rapidata.rapidata_client.audience._audience_base as base_module
from rapidata.api_client.models.create_job_endpoint_cost_warning_model import (
    CreateJobEndpointCostWarningModel,
)
from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase


def _make_audience() -> tuple[RapidataAudienceBase, MagicMock]:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    audience = RapidataAudienceBase(
        id="aud-1", name="Aud", filters=[], openapi_service=openapi_service
    )
    return audience, openapi_service


def test_assign_job_warns_on_cost_warning(monkeypatch):
    audience, openapi_service = _make_audience()
    response = MagicMock()
    response.job_id = "job-1"
    response.cost_warning = CreateJobEndpointCostWarningModel(
        estimatedCost=120.0, availableBalance=50.0, shortfall=70.0
    )
    openapi_service.order.job_api.job_post.return_value = response

    warn = MagicMock()
    monkeypatch.setattr(base_module.logger, "warning", warn)

    audience.assign_job(MagicMock(id="def-1", name="My Job"))

    warn.assert_called_once()
    args = warn.call_args.args
    assert "estimate" in args[0].lower()
    # Values are passed as lazy %-args, not pre-formatted into the message.
    assert 120.0 in args
    assert 50.0 in args
    assert 70.0 in args


def test_assign_job_no_warning_when_cost_within_balance(monkeypatch):
    audience, openapi_service = _make_audience()
    response = MagicMock()
    response.job_id = "job-1"
    response.cost_warning = None
    openapi_service.order.job_api.job_post.return_value = response

    warn = MagicMock()
    monkeypatch.setattr(base_module.logger, "warning", warn)

    job = audience.assign_job(MagicMock(id="def-1", name="My Job"))

    warn.assert_not_called()
    assert job.id == "job-1"
