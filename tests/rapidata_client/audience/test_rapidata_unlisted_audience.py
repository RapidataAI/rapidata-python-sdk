"""Tests for unlisted audiences: creation, lookup by ``ula_`` id, links and jobs.

An unlisted audience is annotated only by the people its owner shares a link with,
so assigning a job points the owner at that link instead of at recruiting.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import rapidata.rapidata_client.audience._audience_base as base_module
from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience
from rapidata.rapidata_client.audience.rapidata_audience_manager import (
    RapidataAudienceManager,
)
from rapidata.rapidata_client.audience._rapidata_unlisted_audience import (
    RapidataUnlistedAudience,
)
from rapidata.rapidata_client.job.rapidata_job import RapidataJob


def _make_service() -> MagicMock:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    return openapi_service


def _make_audience() -> tuple[RapidataUnlistedAudience, MagicMock]:
    openapi_service = _make_service()
    response = MagicMock()
    response.job_id = "job-1"
    response.experiment_id = None
    response.cost_warning = None
    response.content_check_skip_denied = None
    openapi_service.order.job_api.job_post.return_value = response
    audience = RapidataUnlistedAudience(
        id="ula_abc", name="My Team", openapi_service=openapi_service
    )
    return audience, openapi_service


def test_create_unlisted_audience_posts_name_and_returns_audience():
    openapi_service = _make_service()
    unlisted_api = openapi_service.audience.unlisted_audience_api
    unlisted_api.audience_unlisted_post.return_value.audience_id = "ula_abc"

    audience = RapidataAudienceManager(openapi_service).create_unlisted_audience(
        "My Team"
    )

    sent = unlisted_api.audience_unlisted_post.call_args.kwargs[
        "create_unlisted_audience_endpoint_input"
    ]
    assert sent.name == "My Team"
    assert isinstance(audience, RapidataUnlistedAudience)
    assert audience.id == "ula_abc"
    assert audience.name == "My Team"


def test_get_audience_by_id_dispatches_unlisted_ids():
    openapi_service = _make_service()
    unlisted_api = openapi_service.audience.unlisted_audience_api
    unlisted_api.audience_unlisted_audience_id_get.return_value.name = "My Team"

    audience = RapidataAudienceManager(openapi_service).get_audience_by_id("ula_abc")

    unlisted_api.audience_unlisted_audience_id_get.assert_called_once_with(
        audience_id="ula_abc"
    )
    openapi_service.audience.audience_api.audience_audience_id_get.assert_not_called()
    assert isinstance(audience, RapidataUnlistedAudience)
    assert audience.id == "ula_abc"
    assert audience.name == "My Team"


def test_get_audience_by_id_keeps_other_ids_on_the_audience_endpoint():
    openapi_service = _make_service()
    audience_api = openapi_service.audience.audience_api
    audience_api.audience_audience_id_get.return_value.name = "Experts"
    audience_api.audience_audience_id_get.return_value.filters = []

    audience = RapidataAudienceManager(openapi_service).get_audience_by_id("aud_abc")

    openapi_service.audience.unlisted_audience_api.audience_unlisted_audience_id_get.assert_not_called()
    assert isinstance(audience, RapidataAudience)


def test_links_point_at_the_app_label_pages():
    audience, _ = _make_audience()

    assert audience.link == "https://app.rapidata.ai/label/ula_abc"
    assert (
        audience.get_job_link("job-1")
        == "https://app.rapidata.ai/label/ula_abc/job/job-1"
    )


def test_assign_job_shares_link_instead_of_recruiting_warning(monkeypatch, capsys):
    audience, openapi_service = _make_audience()
    warn = MagicMock()
    monkeypatch.setattr(base_module.logger, "warning", warn)

    job = audience.assign_job(MagicMock(id="def-1", name="My Job"))

    sent = openapi_service.order.job_api.job_post.call_args.kwargs[
        "create_job_endpoint_input"
    ]
    assert sent.audience_id == "ula_abc"
    assert job.audience_id == "ula_abc"
    warn.assert_not_called()
    openapi_service.audience.audience_api.audience_audience_id_user_metrics_get.assert_not_called()
    out = capsys.readouterr().out
    assert audience.get_job_link(job) in out
    assert audience.link in out


def test_job_on_unlisted_audience_skips_recruiting_checks():
    openapi_service = _make_service()
    job = RapidataJob(
        job_id="job-1",
        name="My Job",
        audience_id="ula_abc",
        created_at=MagicMock(),
        definition_id="def-1",
        openapi_service=openapi_service,
    )

    job._raise_if_audience_cannot_produce_responses()

    assert job._get_recruiting_metrics() is None
    audience_api = openapi_service.audience.audience_api
    audience_api.audience_audience_id_user_metrics_get.assert_not_called()
    audience_api.audience_audience_id_get.assert_not_called()
