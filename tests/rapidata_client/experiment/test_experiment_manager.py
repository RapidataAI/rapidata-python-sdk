"""Tests for the internal ExperimentManager: create() and run_experiment().

create() must post scope=attached and then activate the returned id.
run_experiment() must reject an empty experiment_id and otherwise delegate to
the audience's job creation, passing the experiment id through.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase
from rapidata.rapidata_client.experiment.experiment_config import ExperimentConfig
from rapidata.rapidata_client.experiment.experiment_manager import (
    Experiment,
    ExperimentManager,
)


def _make_manager() -> tuple[ExperimentManager, MagicMock]:
    openapi_service = MagicMock()
    manager = ExperimentManager(openapi_service=openapi_service)
    return manager, openapi_service


def test_create_posts_attached_scope_then_activates_by_id():
    manager, openapi_service = _make_manager()
    api = openapi_service.campaign.experiment_api

    created = MagicMock(id="exp-1")
    created.name = "job-fast-ui"
    activated = MagicMock(id="exp-1")
    activated.name = "job-fast-ui"
    api.campaign_experiments_post.return_value = created
    api.campaign_experiments_experiment_id_state_post.return_value = activated

    result = manager.create(name="job-fast-ui", treatment_bps=3000)

    post_kwargs = api.campaign_experiments_post.call_args.kwargs
    posted_input = post_kwargs["create_experiment_endpoint_input"]
    assert posted_input.scope == "attached"
    assert posted_input.split.treatment_bps == 3000

    state_args = api.campaign_experiments_experiment_id_state_post.call_args.args
    assert state_args[0] == "exp-1"
    assert state_args[1].action == "activate"

    assert result == Experiment(id="exp-1", name="job-fast-ui", state="active")


def test_run_experiment_raises_on_empty_experiment_id():
    manager, _ = _make_manager()
    config = ExperimentConfig(
        job_definition=MagicMock(id="def-1"),
        experiment_id="",
        audience=MagicMock(id="aud-1"),
    )

    with pytest.raises(ValueError):
        manager.run_experiment(config)


def test_run_experiment_posts_to_audience_id_with_experiment_id():
    manager, _ = _make_manager()
    audience_openapi_service = MagicMock()
    audience_openapi_service.environment = "rapidata.ai"
    response = MagicMock()
    response.job_id = "job-1"
    response.experiment_id = "exp-1"
    response.cost_warning = None
    response.content_check_skip_denied = None
    audience_openapi_service.order.job_api.job_post.return_value = response

    audience = RapidataAudienceBase(
        id="aud-1", name="Aud", filters=[], openapi_service=audience_openapi_service
    )
    job_definition = MagicMock(id="def-1", name="My Job")
    config = ExperimentConfig(
        job_definition=job_definition, experiment_id="exp-1", audience=audience
    )

    job = manager.run_experiment(config)

    call_kwargs = audience_openapi_service.order.job_api.job_post.call_args.kwargs
    posted_input = call_kwargs["create_job_endpoint_input"]
    assert posted_input.audience_id == "aud-1"
    assert posted_input.experiment_id == "exp-1"
    assert job.experiment_id == "exp-1"
