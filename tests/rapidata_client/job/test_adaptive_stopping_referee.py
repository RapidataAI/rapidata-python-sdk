"""AdaptiveStoppingReferee: validation, the compare default, deprecations, and the wire body."""

from __future__ import annotations

import json
import warnings
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
from rapidata.rapidata_client.workflow import ClassifyWorkflow

MACHINE = "rapidata.rapidata_client.job._job_creation_state_machine"
PAIR = ["https://host/a.png", "https://host/b.png"]

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

RESOLVED = {
    "_t": "AdaptiveStoppingReferee",
    "maxVotes": 100,
    "minConfidence": 0.9,
    "ambiguityThreshold": 0.64,
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
        max_votes=40, min_confidence=0.95, ambiguity_threshold=0.75
    )

    assert referee._to_model().to_dict() == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 40,
        "minConfidence": 0.95,
        "ambiguityThreshold": 0.75,
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


def test_votes_count_falls_back_to_the_default_cap_without_max_votes():
    revision = _revision(COMPARE_WORKFLOW, {"_t": "AdaptiveStoppingReferee"})

    assert _votes(revision) == ", 100 votes each"


def test_votes_count_uses_max_votes_when_set():
    revision = _revision(
        COMPARE_WORKFLOW, {"_t": "AdaptiveStoppingReferee", "maxVotes": 35}
    )

    assert _votes(revision) == ", 35 votes each"


# --- create ------------------------------------------------------------------


def _create(method: str = "create_compare_job_definition", **kwargs) -> dict:
    """Run a create method end to end and return the POST body."""
    service = MagicMock()
    service.environment = "rapidata.ai"
    service.dataset.dataset_api.dataset_post.return_value = MagicMock(dataset_id="ds-1")
    service.order.job_api.job_definition_post.return_value = MagicMock(
        definition_id="def-1", pipeline_id="pip-1"
    )
    dataset = MagicMock()
    dataset.id = "ds-1"
    dataset.add_datapoints.side_effect = lambda dps: (dps, [])

    if method == "create_compare_job_definition":
        kwargs.setdefault("datapoints", [PAIR])
    else:
        kwargs.setdefault("datapoints", ["https://host/a.png"])
        kwargs.setdefault("answer_options", ["a", "b"])

    with (
        patch(f"{MACHINE}.RapidataDataset", return_value=dataset),
        patch(f"{MACHINE}.print_job_definition_preview_link"),
    ):
        getattr(RapidataJobManager(service), method)(
            name="n", instruction="Which is sharper?", **kwargs
        )

    post = service.order.job_api.job_definition_post
    body = post.call_args.kwargs["create_job_definition_endpoint_input"]
    return json.loads(json.dumps(body.to_dict(), default=str))


def test_compare_defaults_to_adaptive_stopping_with_backend_defaults():
    body = _create()

    assert body["referee"] == {"_t": "AdaptiveStoppingReferee"}


def test_compare_sends_the_configured_referee():
    body = _create(
        responses_per_datapoint=AdaptiveStoppingReferee(ambiguity_threshold=0.75)
    )

    assert body["referee"] == {
        "_t": "AdaptiveStoppingReferee",
        "ambiguityThreshold": 0.75,
    }


def test_compare_with_an_int_collects_exactly_that_many():
    body = _create(responses_per_datapoint=10)

    assert body["referee"] == {"_t": "NaiveReferee", "totalVotes": 10}


def test_classification_keeps_ten_fixed_responses_by_default():
    body = _create("create_classification_job_definition")

    assert body["referee"] == {"_t": "NaiveReferee", "totalVotes": 10}


def test_quorum_on_compare_keeps_the_old_cap_of_ten():
    body = _create(quorum_threshold=7)

    assert body["referee"] == {"_t": "QuorumReferee", "maxVotes": 10, "threshold": 7}


@pytest.mark.parametrize(
    "method", ["create_compare_job_definition", "create_classification_job_definition"]
)
def test_confidence_threshold_warns_and_keeps_the_old_cap_of_ten(method):
    with pytest.warns(DeprecationWarning, match="confidence_threshold is deprecated"):
        body = _create(method, confidence_threshold=0.99)

    assert body["referee"] == {
        "_t": "EarlyStoppingReferee",
        "threshold": 0.99,
        "maxVotes": 10,
    }


def test_confidence_threshold_warning_points_at_the_callers_line():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _create(confidence_threshold=0.99)

    (warning,) = [w for w in caught if w.category is DeprecationWarning]
    assert warning.filename == __file__


def test_no_deprecation_warning_without_confidence_threshold():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        _create()
        _create(quorum_threshold=7)


@pytest.mark.parametrize(
    "extra", [{"confidence_threshold": 0.99}, {"quorum_threshold": 3}]
)
def test_thresholds_cannot_be_combined_with_an_explicit_adaptive_referee(extra):
    service = MagicMock()
    with pytest.raises(ValueError, match="cannot be combined"):
        RapidataJobManager(service).create_compare_job_definition(
            name="n",
            instruction="Which is sharper?",
            datapoints=[PAIR],
            responses_per_datapoint=AdaptiveStoppingReferee(),
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
            responses_per_datapoint=AdaptiveStoppingReferee(),
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

    jd.responses_per_datapoint = AdaptiveStoppingReferee()
    jd.save()

    assert _sent_referee(service) == {"_t": "AdaptiveStoppingReferee"}


def test_revision_sends_the_configured_referee():
    jd, service = _loaded()

    jd.responses_per_datapoint = AdaptiveStoppingReferee(
        max_votes=30, ambiguity_threshold=0.75
    )
    jd.save()

    assert _sent_referee(service) == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 30,
        "ambiguityThreshold": 0.75,
    }


def test_revision_rejects_adaptive_stopping_on_classify_before_any_request():
    jd, service = _loaded(workflow=CLASSIFY_WORKFLOW)

    with pytest.raises(ValueError, match="only supports compare"):
        jd.responses_per_datapoint = AdaptiveStoppingReferee()

    assert not jd.has_unsaved_changes
    service.order.job_api.job_definition_definition_id_revision_post.assert_not_called()


def test_revision_reads_back_the_resolved_referee():
    jd, _ = _loaded(referee=RESOLVED)

    stopping = jd.responses_per_datapoint
    assert isinstance(stopping, AdaptiveStoppingReferee)
    assert (
        stopping.max_votes,
        stopping.min_confidence,
        stopping.ambiguity_threshold,
    ) == (
        100,
        0.9,
        0.64,
    )


def test_revision_int_on_an_adaptive_definition_switches_to_a_fixed_count():
    jd, service = _loaded(referee=RESOLVED)

    jd.responses_per_datapoint = 10
    jd.save()

    assert _sent_referee(service) == {"_t": "NaiveReferee", "totalVotes": 10}


def test_revision_int_on_a_fixed_definition_keeps_working():
    jd, service = _loaded()

    jd.responses_per_datapoint = 15
    assert jd.responses_per_datapoint == 15
    jd.save()

    assert _sent_referee(service) == {"_t": "NaiveReferee", "totalVotes": 15}
