"""Stopping rules for responses_per_datapoint: AdaptiveStopping, QuorumStopping and a fixed int."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from rapidata import AdaptiveStopping, QuorumStopping
from rapidata.api_client.models.create_job_revision_endpoint_output import (
    CreateJobRevisionEndpointOutput,
)
from rapidata.api_client.models.get_job_revision_endpoint_output import (
    GetJobRevisionEndpointOutput,
)
from rapidata.api_client.models.i_referee import IReferee
from rapidata.rapidata_client.job import rapidata_job_manager
from rapidata.rapidata_client.job.rapidata_job_definition import (
    RapidataJobDefinition,
)
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager
from rapidata.rapidata_client.results import RapidataResults
from rapidata.rapidata_client.settings import AllowNeitherBothSetting, CustomSetting

ADAPTIVE_WIRE = {
    "_t": "AdaptiveStoppingReferee",
    "maxVotes": 100,
    "minConfidence": 0.9,
    "ambiguity": 0.32,
}


class _FakeMachine:
    referee = None

    def __init__(self, **kwargs):
        _FakeMachine.referee = kwargs["referee"]

    def run(self):
        return "created"


@pytest.fixture
def manager(monkeypatch) -> RapidataJobManager:
    monkeypatch.setattr(
        rapidata_job_manager, "JobDefinitionCreationMachine", _FakeMachine
    )
    _FakeMachine.referee = None
    return RapidataJobManager(MagicMock())


def _wire(referee) -> dict:
    return referee._to_model().to_dict()


def _compare(manager: RapidataJobManager, **kwargs) -> dict:
    manager.create_compare_job_definition(
        name="job",
        instruction="Which is better?",
        datapoints=[["a", "b"]],
        data_type="text",
        **kwargs,
    )
    return _wire(_FakeMachine.referee)


def _classify(manager: RapidataJobManager, **kwargs) -> dict:
    manager.create_classification_job_definition(
        name="job",
        instruction="Which?",
        answer_options=["x", "y"],
        datapoints=["a"],
        data_type="text",
        **kwargs,
    )
    return _wire(_FakeMachine.referee)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_confidence": 0},
        {"min_confidence": 1},
        {"ambiguity": 0},
        {"ambiguity": 0.5},
        {"max_responses": 0},
        {"max_responses": 10.0},
    ],
)
def test_adaptive_stopping_rejects_out_of_range_values(kwargs):
    with pytest.raises(ValueError):
        AdaptiveStopping(**kwargs)


def test_quorum_stopping_rejects_threshold_above_max():
    with pytest.raises(ValueError):
        QuorumStopping(threshold=6, max_responses=5)


def test_compare_defaults_to_adaptive_stopping(manager):
    assert _compare(manager) == ADAPTIVE_WIRE


def test_compare_int_stays_a_fixed_number_of_responses(manager):
    assert _compare(manager, responses_per_datapoint=7) == {
        "_t": "NaiveReferee",
        "totalVotes": 7,
    }


def test_compare_custom_adaptive_and_quorum(manager):
    custom = AdaptiveStopping(min_confidence=0.95, ambiguity=0.4, max_responses=50)
    assert _compare(manager, responses_per_datapoint=custom) == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 50,
        "minConfidence": 0.95,
        "ambiguity": 0.4,
    }
    assert _compare(manager, responses_per_datapoint=QuorumStopping(3, 5)) == {
        "_t": "QuorumReferee",
        "maxVotes": 5,
        "threshold": 3,
    }


def test_deprecated_quorum_threshold_keeps_the_old_cap(manager):
    with pytest.warns(DeprecationWarning, match="quorum_threshold"):
        wire = _compare(manager, quorum_threshold=3)
    assert wire == {"_t": "QuorumReferee", "maxVotes": 10, "threshold": 3}


def test_deprecated_confidence_threshold_with_int(manager):
    with pytest.warns(DeprecationWarning, match="confidence_threshold"):
        wire = _compare(manager, confidence_threshold=0.99, responses_per_datapoint=20)
    assert wire["_t"] == "EarlyStoppingReferee"
    assert wire["maxVotes"] == 20


@pytest.mark.parametrize(
    "config", [AdaptiveStopping(), QuorumStopping(threshold=3, max_responses=5)]
)
def test_deprecated_threshold_with_config_object_raises(manager, config):
    with pytest.raises(ValueError, match="cannot be combined"):
        _compare(manager, quorum_threshold=3, responses_per_datapoint=config)


@pytest.mark.parametrize(
    "setting", [AllowNeitherBothSetting(), CustomSetting("compare_unsure", "0")]
)
def test_adaptive_with_unsure_button_raises(manager, setting):
    with pytest.raises(ValueError, match="QuorumStopping"):
        _compare(manager, settings=[setting])


def test_unsure_button_with_fixed_responses_is_fine(manager):
    wire = _compare(
        manager, responses_per_datapoint=10, settings=[AllowNeitherBothSetting()]
    )
    assert wire["_t"] == "NaiveReferee"


def test_classification_rejects_adaptive_stopping(manager):
    with pytest.raises(ValueError, match="only supported for compare"):
        _classify(manager, responses_per_datapoint=AdaptiveStopping())


def test_classification_accepts_quorum_stopping(manager):
    wire = _classify(manager, responses_per_datapoint=QuorumStopping(3, 5))
    assert wire == {"_t": "QuorumReferee", "maxVotes": 5, "threshold": 3}
    assert _classify(manager) == {"_t": "NaiveReferee", "totalVotes": 10}


def test_adaptive_referee_round_trips_through_the_generated_union():
    model = IReferee.from_dict(ADAPTIVE_WIRE)
    assert type(model.actual_instance).__name__ == "IRefereeAdaptiveStoppingReferee"
    assert model.to_dict() == ADAPTIVE_WIRE


def _compare_revision(referee: dict, flags: list | None = None):
    data = {
        "definitionId": "jd-1",
        "revisionNumber": 3,
        "state": "Completed",
        "pipelineId": "pip-1",
        "datasetId": "ds-1",
        "aggregatorType": None,
        "workflow": {
            "_t": "SimpleWorkflow",
            "rapid": {
                "_t": "Compare",
                "asset": {"segment": "asset"},
                "criteria": {"literal": "Which is better?"},
            },
            "featureFlags": [],
        },
        "referee": referee,
        "featureFlags": flags or [],
        "campaignFeatureFlags": [],
        "validationSetId": None,
        "baseRevisionNumber": 2,
        "createdAt": "2026-10-23T12:00:00Z",
        "createdById": "00000000-0000-0000-0000-000000000001",
        "createdByMail": "a@rapidata.ai",
    }
    service = MagicMock()
    job_api = service.order.job_api
    revision = GetJobRevisionEndpointOutput.from_dict(data)
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


def test_job_definition_reads_config_objects():
    jd, _ = _compare_revision(ADAPTIVE_WIRE)
    assert jd.responses_per_datapoint == AdaptiveStopping()

    jd, _ = _compare_revision({"_t": "QuorumReferee", "maxVotes": 5, "threshold": 3})
    assert jd.responses_per_datapoint == QuorumStopping(threshold=3, max_responses=5)


@pytest.mark.parametrize(
    "value, wire",
    [
        (AdaptiveStopping(max_responses=40), {**ADAPTIVE_WIRE, "maxVotes": 40}),
        (QuorumStopping(2, 3), {"_t": "QuorumReferee", "maxVotes": 3, "threshold": 2}),
        (12, {"_t": "NaiveReferee", "totalVotes": 12}),
    ],
)
def test_job_definition_setter_replaces_the_rule(value, wire):
    jd, service = _compare_revision({"_t": "NaiveReferee", "totalVotes": 10})
    jd.responses_per_datapoint = value
    assert jd.responses_per_datapoint == value
    jd.save()
    assert _sent_referee(service) == wire


def test_int_on_legacy_confidence_referee_tunes_its_cap():
    legacy = {"_t": "EarlyStoppingReferee", "maxVotes": 10, "threshold": 0.99}
    jd, service = _compare_revision(legacy)
    assert jd.responses_per_datapoint == 10
    jd.responses_per_datapoint = 30
    jd.save()
    assert _sent_referee(service) == {**legacy, "maxVotes": 30}


def test_job_definition_rejects_adaptive_with_unsure_flag_on_save():
    jd, service = _compare_revision(
        {"_t": "NaiveReferee", "totalVotes": 10},
        flags=[{"key": "compare_unsure", "value": "5000"}],
    )
    jd.responses_per_datapoint = AdaptiveStopping()
    with pytest.raises(ValueError, match="AllowNeitherBothSetting"):
        jd.save()
    service.order.job_api.job_definition_definition_id_revision_post.assert_not_called()


def test_results_expose_verdict_and_responses():
    def row(state):
        return {
            "aggregatedResults": {"a.png": 9, "b.png": 1},
            "stoppingState": state,
        }

    base = {"weightA": 1.0, "weightB": 1.0, "csLower": 0.1, "csUpper": 0.9}
    results = RapidataResults(
        {
            "info": {"type": "Compare"},
            "results": [
                row({**base, "verdict": "A", "decidedAtResponse": 7}),
                row({**base, "verdict": "Ambiguous", "decidedAtResponse": 16}),
                row({**base, "verdict": "Undecided", "decidedAtResponse": None}),
                row({**base, "verdict": None, "decidedAtResponse": None}),
                {"aggregatedResults": {"a.png": 5, "b.png": 5}},
            ],
        }
    )
    rows = results["results"]
    assert [r.get("verdict") for r in rows] == [
        "A",
        "ambiguous",
        "undecided",
        None,
        None,
    ]
    assert [r.get("responses") for r in rows] == [7, 16, 10, 10, None]
    assert "verdict" not in rows[4]
