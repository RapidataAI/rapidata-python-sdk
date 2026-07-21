"""Tests for the no-graduated-annotators warning surfaced by assign_job.

A dimension audience only produces responses once annotators graduate into it,
which needs qualification examples and started recruiting. Assigning a job while
no annotator has graduated means the job receives zero responses, so assign_job
logs an advisory warning. The job is created regardless; a filtered audience
(which reuses its base's qualified pool) never warns.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import rapidata.rapidata_client.audience.rapidata_audience as audience_module
from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience


def _make_audience(
    users_per_state: dict[str, int],
) -> tuple[RapidataAudience, MagicMock]:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"

    response = MagicMock()
    response.job_id = "job-1"
    response.cost_warning = None
    openapi_service.order.job_api.job_post.return_value = response

    openapi_service.audience.audience_api.audience_audience_id_user_metrics_get.return_value.users_per_state = (
        users_per_state
    )

    audience = RapidataAudience(
        id="aud-1", name="My Audience", filters=[], openapi_service=openapi_service
    )
    return audience, openapi_service


def test_assign_job_warns_when_no_annotators_have_graduated(monkeypatch):
    # Recruiting is underway (some distilling) but nobody has graduated yet.
    audience, _ = _make_audience({"Distilling": 5})

    warn = MagicMock()
    monkeypatch.setattr(audience_module.logger, "warning", warn)

    audience.assign_job(MagicMock(id="def-1", name="My Job"))

    warn.assert_called_once()
    message = warn.call_args.args[0].lower()
    assert "graduate" in message
    assert "global" in message


def test_assign_job_no_warning_when_audience_has_graduated_annotators(monkeypatch):
    audience, _ = _make_audience({"Graduated": 12, "Distilling": 3})

    warn = MagicMock()
    monkeypatch.setattr(audience_module.logger, "warning", warn)

    job = audience.assign_job(MagicMock(id="def-1", name="My Job"))

    warn.assert_not_called()
    assert job.id == "job-1"
