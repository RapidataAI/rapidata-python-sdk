"""AdaptiveStoppingReferee: validation, compare-only, and the wire body on create and revision."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from rapidata import AdaptiveStoppingReferee
from rapidata.api_client.models.create_job_revision_endpoint_output import (
    CreateJobRevisionEndpointOutput,
)
from rapidata.api_client.models.get_job_revision_endpoint_output import (
    GetJobRevisionEndpointOutput,
)
from rapidata.rapidata_client.job.rapidata_job_definition import (
    RapidataJobDefinition,
)
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager
from rapidata.rapidata_client.job.rapidata_template_manager import _votes
from rapidata.rapidata_client.referee import NaiveReferee
from rapidata.rapidata_client.workflow import ClassifyWorkflow

MACHINE = "rapidata.rapidata_client.job._job_creation_state_machine"

COMPARE_WORKFLOW = {
    "_t": "SimpleWorkflow",
    "rapid": {
        "_t": "Compare",
        "asset": {"segment": "asset"},
        "criteria": {"literal": "Which is sharper?"},
    },
    "featureFlags": [],
}

CLASSIFY_WORKFLOW = {
    "_t": "SimpleWorkflow",
    "rapid": {
        "_t": "Classify",
        "asset": {"segment": "asset"},
        "title": {"literal": "Which is sharper?"},
        "categories": {"literal": [{"label": "a", "value": "a"}]},
    },
    "featureFlags": [],
}


# --- validation -------------------------------------------------------------


def test_defaults_are_left_to_the_backend():
    referee = AdaptiveStoppingReferee()

    assert referee.max_votes is None
    assert referee.min_confidence is None
    assert referee.ambiguity_threshold is None
    assert referee._to_model().to_dict() == {"_t": "AdaptiveStoppingReferee"}


def test_set_fields_go_out_with_their_wire_names():
    referee = AdaptiveStoppingReferee(
        max_votes=40, min_confidence=0.95, ambiguity_threshold=0.7
    )

    assert referee._to_model().to_dict() == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 40,
        "minConfidence": 0.95,
        "ambiguityThreshold": 0.7,
    }


@pytest.mark.parametrize("max_votes", [0, -1, 1.5, True, "10"])
def test_max_votes_must_be_a_positive_integer(max_votes):
    with pytest.raises(ValueError, match="max_votes"):
        AdaptiveStoppingReferee(max_votes=max_votes)


@pytest.mark.parametrize("field", ["min_confidence", "ambiguity_threshold"])
@pytest.mark.parametrize("value", [0, 1, 0.0, 1.0, -0.1, 1.1, True, "0.5"])
def test_probabilities_must_be_strictly_between_zero_and_one(field, value):
    with pytest.raises(ValueError, match=field):
        AdaptiveStoppingReferee(**{field: value})


@pytest.mark.parametrize("value", [0.01, 0.5, 0.99])
def test_probabilities_inside_the_open_interval_are_accepted(value):
    referee = AdaptiveStoppingReferee(min_confidence=value, ambiguity_threshold=value)

    assert referee.min_confidence == referee.ambiguity_threshold == value


# --- cost and progress count max_votes per datapoint -------------------------


def test_responses_per_datapoint_is_the_backend_default_without_max_votes():
    assert AdaptiveStoppingReferee()._responses_per_datapoint == 100


def test_responses_per_datapoint_is_max_votes_when_set():
    assert AdaptiveStoppingReferee(max_votes=25)._responses_per_datapoint == 25


# --- create ------------------------------------------------------------------


def _create_compare(**kwargs) -> dict:
    """Run create_compare_job_definition end to end and return the POST body."""
    service = MagicMock()
    service.environment = "rapidata.ai"
    service.dataset.dataset_api.dataset_post.return_value = MagicMock(dataset_id="ds-1")
    service.order.job_api.job_definition_post.return_value = MagicMock(
        definition_id="def-1", pipeline_id="pip-1"
    )
    dataset = MagicMock()
    dataset.id = "ds-1"
    dataset.add_datapoints.side_effect = lambda dps: (dps, [])

    with (
        patch(f"{MACHINE}.RapidataDataset", return_value=dataset),
        patch(f"{MACHINE}.print_job_definition_preview_link"),
    ):
        RapidataJobManager(service).create_compare_job_definition(
            name="n",
            instruction="Which is sharper?",
            datapoints=[["https://host/a.png", "https://host/b.png"]],
            **kwargs,
        )

    post = service.order.job_api.job_definition_post
    body = post.call_args.kwargs["create_job_definition_endpoint_input"]
    return json.loads(json.dumps(body.to_dict(), default=str))


def test_compare_create_sends_the_bare_referee_for_backend_defaults():
    body = _create_compare(referee=AdaptiveStoppingReferee())

    assert body["referee"] == {"_t": "AdaptiveStoppingReferee"}


def test_compare_create_sends_the_configured_referee():
    body = _create_compare(
        referee=AdaptiveStoppingReferee(
            max_votes=60, min_confidence=0.9, ambiguity_threshold=0.64
        )
    )

    assert body["referee"] == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 60,
        "minConfidence": 0.9,
        "ambiguityThreshold": 0.64,
    }


def test_compare_create_without_referee_keeps_ten_fixed_responses():
    body = _create_compare()

    assert body["referee"] == {"_t": "NaiveReferee", "totalVotes": 10}


@pytest.mark.parametrize(
    "extra",
    [
        {"responses_per_datapoint": 20},
        {"confidence_threshold": 0.99},
        {"quorum_threshold": 3},
    ],
)
def test_compare_create_rejects_a_second_stopping_rule(extra):
    service = MagicMock()
    with pytest.raises(ValueError, match="referee"):
        RapidataJobManager(service).create_compare_job_definition(
            name="n",
            instruction="Which is sharper?",
            datapoints=[["https://host/a.png", "https://host/b.png"]],
            referee=AdaptiveStoppingReferee(),
            **extra,
        )
    service.order.job_api.job_definition_post.assert_not_called()


def test_non_compare_create_is_rejected_before_any_request():
    service = MagicMock()
    with pytest.raises(ValueError, match="only supports compare"):
        RapidataJobManager(service)._create_general_job_definition(
            name="n",
            workflow=ClassifyWorkflow(instruction="What is it?"),
            datapoints=[],
            referee=AdaptiveStoppingReferee(),
        )
    service.dataset.dataset_api.dataset_post.assert_not_called()
    service.order.job_api.job_definition_post.assert_not_called()


# --- revision ----------------------------------------------------------------


def _revision(workflow: dict, referee: dict) -> GetJobRevisionEndpointOutput:
    model = GetJobRevisionEndpointOutput.from_dict(
        {
            "definitionId": "jd-1",
            "revisionNumber": 3,
            "state": "Completed",
            "pipelineId": "pip-1",
            "datasetId": "ds-1",
            "aggregatorType": None,
            "workflow": workflow,
            "referee": referee,
            "featureFlags": [],
            "campaignFeatureFlags": [],
            "validationSetId": None,
            "baseRevisionNumber": 2,
            "createdAt": "2026-10-23T12:00:00Z",
            "createdById": "00000000-0000-0000-0000-000000000001",
            "createdByMail": "a@rapidata.ai",
        }
    )
    assert model is not None
    return model


def _loaded(
    workflow: dict = COMPARE_WORKFLOW,
    referee: dict | None = None,
) -> tuple[RapidataJobDefinition, MagicMock]:
    revision = _revision(workflow, referee or {"_t": "NaiveReferee", "totalVotes": 10})
    service = MagicMock()
    service.environment = "rapidata.ai"
    job_api = service.order.job_api
    job_api.job_definition_definition_id_revision_get.return_value = revision
    job_api.job_definition_definition_id_revision_revision_number_get.return_value = (
        revision
    )
    job_api.job_definition_definition_id_revision_post.return_value = (
        CreateJobRevisionEndpointOutput(revisionNumber=4, pipelineId="pip-x")
    )
    return RapidataJobDefinition("jd-1", "Job", service).reload(), service


def _sent_referee(service: MagicMock) -> dict:
    post = service.order.job_api.job_definition_definition_id_revision_post
    body = post.call_args.kwargs["create_job_revision_endpoint_input"]
    return json.loads(json.dumps(body.to_dict(), default=str))["referee"]


def test_revision_switches_a_compare_definition_to_adaptive_stopping():
    jd, service = _loaded()

    jd.referee = AdaptiveStoppingReferee()
    jd.save()

    assert _sent_referee(service) == {"_t": "AdaptiveStoppingReferee"}


def test_revision_sends_the_configured_referee():
    jd, service = _loaded()

    jd.referee = AdaptiveStoppingReferee(max_votes=30, ambiguity_threshold=0.8)
    jd.save()

    assert _sent_referee(service) == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 30,
        "ambiguityThreshold": 0.8,
    }


def test_revision_rejects_adaptive_stopping_on_classify_before_any_request():
    jd, service = _loaded(workflow=CLASSIFY_WORKFLOW)

    with pytest.raises(ValueError, match="only supports compare"):
        jd.referee = AdaptiveStoppingReferee()

    assert not jd.has_unsaved_changes
    service.order.job_api.job_definition_definition_id_revision_post.assert_not_called()


def test_revision_reads_back_the_resolved_referee():
    jd, _ = _loaded(
        referee={
            "_t": "AdaptiveStoppingReferee",
            "maxVotes": 100,
            "minConfidence": 0.9,
            "ambiguityThreshold": 0.64,
        }
    )

    referee = jd.referee
    assert isinstance(referee, AdaptiveStoppingReferee)
    assert (referee.max_votes, referee.min_confidence, referee.ambiguity_threshold) == (
        100,
        0.9,
        0.64,
    )
    assert jd.responses_per_datapoint == 100


def test_revision_responses_per_datapoint_changes_max_votes_only():
    jd, service = _loaded(
        referee={
            "_t": "AdaptiveStoppingReferee",
            "maxVotes": 100,
            "minConfidence": 0.9,
            "ambiguityThreshold": 0.64,
        }
    )

    jd.responses_per_datapoint = 40
    jd.save()

    assert _sent_referee(service) == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 40,
        "minConfidence": 0.9,
        "ambiguityThreshold": 0.64,
    }


def test_setting_the_referee_replaces_a_staged_response_count():
    jd, service = _loaded()

    jd.responses_per_datapoint = 15
    jd.referee = AdaptiveStoppingReferee()
    assert jd.responses_per_datapoint == 100
    jd.save()

    assert _sent_referee(service) == {"_t": "AdaptiveStoppingReferee"}


def test_a_response_count_staged_after_the_referee_sets_its_max_votes():
    jd, service = _loaded()

    jd.referee = AdaptiveStoppingReferee(min_confidence=0.95)
    jd.responses_per_datapoint = 20
    assert jd.referee.max_votes == 20  # type: ignore[union-attr]
    jd.save()

    assert _sent_referee(service) == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 20,
        "minConfidence": 0.95,
    }


def test_revision_reads_other_referees_back_as_their_classes():
    jd, _ = _loaded()

    referee = jd.referee
    assert isinstance(referee, NaiveReferee)
    assert referee.responses == 10


# --- cost and progress on saved revisions ------------------------------------


def test_votes_count_falls_back_to_the_default_cap_without_max_votes():
    revision = _revision(COMPARE_WORKFLOW, {"_t": "AdaptiveStoppingReferee"})

    assert _votes(revision) == ", 100 votes each"


def test_votes_count_uses_max_votes_when_set():
    revision = _revision(
        COMPARE_WORKFLOW, {"_t": "AdaptiveStoppingReferee", "maxVotes": 35}
    )

    assert _votes(revision) == ", 35 votes each"
