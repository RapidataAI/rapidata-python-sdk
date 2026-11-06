"""Stopping rules for responses_per_datapoint: AdaptiveStopping, QuorumStopping and a fixed int."""

from __future__ import annotations

import json
import warnings
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
from rapidata.api_client.models.i_referee_config import IRefereeConfig
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
    "ambiguityThreshold": 0.64,
    "unsolvableThreshold": 0.5,
    "maxOutcomeCount": 1,
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
        {"ambiguity_threshold": 0},
        {"ambiguity_threshold": 1},
        {"ambiguity_threshold": 1.5},
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
    custom = AdaptiveStopping(
        min_confidence=0.95, ambiguity_threshold=0.75, max_responses=50
    )
    assert _compare(manager, responses_per_datapoint=custom) == {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 50,
        "minConfidence": 0.95,
        "ambiguityThreshold": 0.75,
        "unsolvableThreshold": 0.5,
        "maxOutcomeCount": 1,
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
def test_adaptive_works_with_unsure_button(manager, setting):
    assert _compare(manager, settings=[setting]) == ADAPTIVE_WIRE


def test_confidence_threshold_is_not_deprecated_on_classification(manager):
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        wire = _classify(manager, confidence_threshold=0.99)
    assert wire["_t"] == "EarlyStoppingReferee"
    assert wire["maxVotes"] == 10


def test_quorum_threshold_is_deprecated_on_classification(manager):
    with pytest.warns(DeprecationWarning, match="quorum_threshold"):
        _classify(manager, quorum_threshold=3)


def test_classification_accepts_explicit_adaptive_stopping(manager):
    assert (
        _classify(manager, responses_per_datapoint=AdaptiveStopping()) == ADAPTIVE_WIRE
    )


def test_binary_compare_rejects_leading_sets_of_two(manager):
    with pytest.raises(ValueError, match="max_outcome_count"):
        _compare(manager, responses_per_datapoint=AdaptiveStopping(max_outcome_count=2))


def test_both_neither_compare_allows_three_of_four_outcomes(manager):
    assert _compare(
        manager,
        responses_per_datapoint=AdaptiveStopping(max_outcome_count=3),
        allow_both_good=True,
        allow_both_bad=True,
    ) == {**ADAPTIVE_WIRE, "maxOutcomeCount": 3}


def test_campaign_flag_cannot_expand_the_compare_outcome_count(manager):
    with pytest.raises(ValueError, match="max_outcome_count"):
        _compare(
            manager,
            responses_per_datapoint=AdaptiveStopping(max_outcome_count=3),
            settings=[CustomSetting("compare_unsure", "5000", target="campaign")],
        )


def test_classify_accepts_three_of_six_but_rejects_a_set_covering_every_outcome(
    manager,
):
    manager.create_classification_job_definition(
        name="Job",
        instruction="Which?",
        answer_options=["a", "b", "c", "d", "e", "f"],
        datapoints=["text"],
        data_type="text",
        responses_per_datapoint=AdaptiveStopping(max_outcome_count=3),
    )
    assert _wire(_FakeMachine.referee) == {**ADAPTIVE_WIRE, "maxOutcomeCount": 3}
    with pytest.raises(ValueError, match="max_outcome_count"):
        _classify(
            manager, responses_per_datapoint=AdaptiveStopping(max_outcome_count=2)
        )


def test_classify_validates_the_set_limit_for_every_datapoint(manager):
    with pytest.raises(ValueError, match="max_outcome_count"):
        manager.create_classification_job_definition(
            name="Job",
            instruction="Which?",
            answer_options=[["a", "b", "c", "d", "e", "f"], ["yes", "no"]],
            datapoints=["first", "second"],
            data_type="text",
            responses_per_datapoint=AdaptiveStopping(max_outcome_count=3),
        )


def test_classification_accepts_quorum_stopping(manager):
    wire = _classify(manager, responses_per_datapoint=QuorumStopping(3, 5))
    assert wire == {"_t": "QuorumReferee", "maxVotes": 5, "threshold": 3}
    assert _classify(manager) == {"_t": "NaiveReferee", "totalVotes": 10}


def test_adaptive_referee_round_trips_through_the_generated_union():
    model = IReferee.from_dict(ADAPTIVE_WIRE)
    assert isinstance(model, IReferee)
    assert model.to_dict() == ADAPTIVE_WIRE


@pytest.mark.parametrize("union", [IRefereeConfig])
def test_workflow_config_unions_preserve_discriminator_and_all_settings(union):
    config = {
        "_t": "AdaptiveStoppingRefereeConfig",
        "maxVotes": 47,
        "minConfidence": 0.95,
        "ambiguityThreshold": 0.73,
        "unsolvableThreshold": 0.6,
        "maxOutcomeCount": 3,
    }
    assert union.from_dict(config).to_dict() == config


@pytest.mark.parametrize("union", [IReferee, IRefereeConfig])
def test_legacy_wire_reads_write_only_canonical_fields(union):
    discriminator = (
        "AdaptiveStoppingReferee"
        if union is IReferee
        else "AdaptiveStoppingRefereeConfig"
    )
    legacy = {
        "_t": discriminator,
        "maxVotes": 100,
        "minConfidence": 0.9,
        "ambiguityRange": 0.6,
    }

    assert union.from_dict(legacy).to_dict() == {**ADAPTIVE_WIRE, "_t": discriminator}


def _compare_revision(
    referee: dict,
    flags: list | None = None,
    workflow: dict | None = None,
    **controls,
):
    data = {
        "definitionId": "jd-1",
        "revisionNumber": 3,
        "state": "Completed",
        "pipelineId": "pip-1",
        "datasetId": "ds-1",
        "aggregatorType": None,
        "workflow": workflow
        or {
            "_t": "SimpleWorkflow",
            "rapid": {
                "_t": "Compare",
                "asset": {"segment": "asset"},
                "criteria": {"literal": "Which is better?"},
                "allowBothGood": False,
                "allowBothBad": False,
                "allowCantSolve": False,
                **controls,
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

    without_cap = {k: v for k, v in ADAPTIVE_WIRE.items() if k != "maxVotes"}
    jd, _ = _compare_revision(without_cap)
    assert jd.responses_per_datapoint == AdaptiveStopping(max_responses=100)

    jd, _ = _compare_revision({"_t": "QuorumReferee", "maxVotes": 5, "threshold": 3})
    assert jd.responses_per_datapoint == QuorumStopping(threshold=3, max_responses=5)


def test_fixed_replacement_does_not_decode_obsolete_adaptive_fields(monkeypatch):
    jd, service = _compare_revision(
        {
            "_t": "AdaptiveStoppingReferee",
            "maxVotes": 47,
            "minConfidence": 0.95,
            "ambiguityThreshold": 0.73,
            "unsolvableThreshold": 0.6,
            "maxOutcomeCount": 3,
        }
    )

    decode = MagicMock(
        side_effect=AssertionError("Saved adaptive decoder must not run")
    )
    monkeypatch.setattr(
        "rapidata.rapidata_client.job.rapidata_job_definition._get_responses", decode
    )
    jd.responses_per_datapoint = 12

    assert jd.responses_per_datapoint == 12
    jd.save()
    assert _sent_referee(service) == {"_t": "NaiveReferee", "totalVotes": 12}
    decode.assert_not_called()


def test_instruction_edit_preserves_every_resolved_adaptive_setting():
    wire = {
        "_t": "AdaptiveStoppingReferee",
        "maxVotes": 47,
        "minConfidence": 0.95,
        "ambiguityThreshold": 0.73,
        "unsolvableThreshold": 0.6,
        "maxOutcomeCount": 3,
    }
    jd, service = _compare_revision(
        wire,
        flags=[{"key": "compare_unsure", "value": "5000"}],
        allowBothGood=True,
        allowBothBad=True,
        allowCantSolve=True,
    )

    assert jd.responses_per_datapoint == AdaptiveStopping(
        min_confidence=0.95,
        ambiguity_threshold=0.73,
        max_responses=47,
        max_outcome_count=3,
        unsolvable_threshold=0.6,
    )
    jd.instruction = "Which fits the description?"
    jd.save()

    assert _sent_referee(service) == wire


def test_classification_revisions_validate_the_final_category_count():
    workflow = {
        "_t": "SimpleWorkflow",
        "rapid": {
            "_t": "Classify",
            "asset": {"segment": "asset"},
            "title": {"literal": "Which?"},
            "categories": {
                "literal": [{"label": str(i), "value": f"value.{i}"} for i in range(6)]
            },
        },
        "featureFlags": [],
    }
    wire = {**ADAPTIVE_WIRE, "maxOutcomeCount": 3}
    jd, service = _compare_revision(wire, workflow=workflow)
    assert jd.responses_per_datapoint.max_outcome_count == 3
    jd.instruction = "Which category fits?"
    jd.save()
    assert _sent_referee(service) == wire

    jd, service = _compare_revision(wire, workflow=workflow)
    jd.answer_options = ["yes", "no"]
    with pytest.raises(ValueError, match="max_outcome_count"):
        jd.save()
    service.order.job_api.job_definition_definition_id_revision_post.assert_not_called()


def test_removing_a_rendering_hint_keeps_explicit_outcome_eligibility():
    wire = {**ADAPTIVE_WIRE, "maxOutcomeCount": 3}
    jd, service = _compare_revision(
        wire,
        flags=[{"key": "compare_unsure", "value": "5000"}],
        allowBothGood=True,
        allowBothBad=True,
    )
    jd.settings = []
    jd.save()
    assert _sent_referee(service) == wire
    body = service.order.job_api.job_definition_definition_id_revision_post.call_args.kwargs[
        "create_job_revision_endpoint_input"
    ].to_dict()
    assert body["workflow"]["rapid"]["allowBothGood"] is True
    assert body["workflow"]["rapid"]["allowBothBad"] is True


def test_disabling_a_substantive_outcome_requires_a_smaller_leading_set():
    jd, service = _compare_revision(
        {**ADAPTIVE_WIRE, "maxOutcomeCount": 3},
        allowBothGood=True,
        allowBothBad=True,
    )
    assert jd.allow_both_good is True
    assert jd.allow_both_bad is True
    assert jd.allow_cant_solve is False
    jd.allow_both_bad = False
    assert jd.allow_both_bad is False
    with pytest.raises(ValueError, match="max_outcome_count"):
        jd.save()
    service.order.job_api.job_definition_definition_id_revision_post.assert_not_called()
    jd.responses_per_datapoint = AdaptiveStopping()
    jd.save()
    assert _sent_referee(service) == ADAPTIVE_WIRE


@pytest.mark.parametrize(
    "setting", [AllowNeitherBothSetting(), CustomSetting("compare_unsure", "0")]
)
def test_rendering_hints_never_enable_extra_outcomes(manager, setting):
    with pytest.raises(ValueError, match="max_outcome_count"):
        _compare(
            manager,
            responses_per_datapoint=AdaptiveStopping(max_outcome_count=2),
            settings=[setting],
        )


@pytest.mark.parametrize(
    "controls",
    [
        {"allow_both_good": True},
        {"allow_both_bad": True},
        {"allow_both_good": True, "allow_cant_solve": True},
    ],
)
def test_one_additional_compare_outcome_permits_two_leading_alternatives(
    manager, controls
):
    assert (
        _compare(
            manager,
            responses_per_datapoint=AdaptiveStopping(max_outcome_count=2),
            **controls,
        )["maxOutcomeCount"]
        == 2
    )
    with pytest.raises(ValueError, match="max_outcome_count"):
        _compare(
            manager,
            responses_per_datapoint=AdaptiveStopping(max_outcome_count=3),
            **controls,
        )


@pytest.mark.parametrize("task", [_compare, _classify])
def test_cant_solve_is_excluded_from_the_substantive_outcome_count(manager, task):
    with pytest.raises(ValueError, match="max_outcome_count"):
        task(
            manager,
            allow_cant_solve=True,
            responses_per_datapoint=AdaptiveStopping(max_outcome_count=2),
        )


@pytest.mark.parametrize(
    "control", ["allow_both_good", "allow_both_bad", "allow_cant_solve"]
)
@pytest.mark.parametrize("value", [None, 0, 1, "false", [], {}])
def test_answer_controls_require_actual_booleans(manager, control, value):
    with pytest.raises(ValueError, match="must be a bool"):
        _compare(manager, **{control: value})
    if control == "allow_cant_solve":
        with pytest.raises(ValueError, match="must be a bool"):
            _classify(manager, **{control: value})


def test_classification_revision_preserves_cant_solve_and_exact_category_values():
    values = ["arbitrary.string", "雪❄️", "a0", "bothGood", "value 4", "c0"]
    workflow = {
        "_t": "SimpleWorkflow",
        "rapid": {
            "_t": "Classify",
            "asset": {"segment": "asset"},
            "title": {"literal": "Which?"},
            "allowCantSolve": True,
            "categories": {
                "literal": [
                    {"label": label, "value": value}
                    for label, value in zip(reversed(values), values)
                ]
            },
        },
    }
    wire = {**ADAPTIVE_WIRE, "maxOutcomeCount": 3}
    jd, service = _compare_revision(wire, workflow=workflow)
    assert jd.allow_cant_solve is True
    assert jd.allow_both_good is None
    assert jd.allow_both_bad is None
    jd.instruction = "Revised question"
    jd.allow_cant_solve = False
    jd.save()
    body = service.order.job_api.job_definition_definition_id_revision_post.call_args.kwargs[
        "create_job_revision_endpoint_input"
    ].to_dict()
    rapid = body["workflow"]["rapid"]
    assert rapid["allowCantSolve"] is False
    assert rapid["categories"]["literal"] == workflow["rapid"]["categories"]["literal"]
    assert body["referee"] == wire
    with pytest.raises(ValueError, match="no allow_both_good"):
        jd.allow_both_good = True


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


def test_job_definition_saves_adaptive_with_unsure_flag():
    jd, service = _compare_revision(
        {"_t": "NaiveReferee", "totalVotes": 10},
        flags=[{"key": "compare_unsure", "value": "5000"}],
    )
    jd.responses_per_datapoint = AdaptiveStopping()
    jd.save()
    assert _sent_referee(service) == ADAPTIVE_WIRE


def test_results_expose_verdict_and_responses():
    def row(verdict, count):
        return {
            "aggregatedResults": {"a.png": 9, "b.png": 1},
            "stoppingState": {
                "weightA": 1.0,
                "weightB": 1.0,
                "csLower": 0.1,
                "csUpper": 0.9,
                "verdict": verdict,
                "responseCount": count,
                "minConfidence": 0.9,
                "ambiguityRange": 0.6,
            },
        }

    results = RapidataResults(
        {
            "info": {"type": "Compare"},
            "results": [
                row("A", 7),
                row("Ambiguous", 16),
                row("Undecided", 100),
                row("Open", 4),
                {"aggregatedResults": {"a.png": 5, "b.png": 5}},
            ],
        }
    )
    rows = results["results"]
    assert [r.get("verdict") for r in rows[:4]] == [
        "A",
        "ambiguous",
        "undecided",
        "open",
    ]
    assert [r.get("responses") for r in rows[:4]] == [7, 16, 100, 4]
    assert "verdict" not in rows[4]
    assert "responses" not in rows[4]


@pytest.mark.parametrize(
    "legacy,threshold",
    [
        ({"ambiguityRange": 0.6}, 0.64),
        ({"ambiguityRange": 0.3}, 0.91),
        ({"ambiguityRange": "ignored", "ambiguityThreshold": 0.73}, 0.73),
    ],
)
def test_saved_definition_legacy_config_reads_and_unrelated_edits_write_canonical_input(
    legacy, threshold
):
    wire = {"_t": "AdaptiveStoppingReferee", **legacy}
    jd, service = _compare_revision(wire, allowCantSolve=False)
    assert jd.responses_per_datapoint == AdaptiveStopping(ambiguity_threshold=threshold)
    assert jd.allow_cant_solve is False
    jd.instruction = "Which response fits the instruction?"
    jd.save()
    assert _sent_referee(service) == {**ADAPTIVE_WIRE, "ambiguityThreshold": threshold}
