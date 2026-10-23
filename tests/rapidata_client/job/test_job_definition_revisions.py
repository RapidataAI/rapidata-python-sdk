"""RapidataJobDefinition holds one revision; save() sends it whole, built from that revision."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.create_job_revision_endpoint_output import (
    CreateJobRevisionEndpointOutput,
)
from rapidata.api_client.models.get_job_revision_endpoint_output import (
    GetJobRevisionEndpointOutput,
)
from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase
from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError
from rapidata.rapidata_client.exceptions.revision_conflict_error import (
    RevisionConflictError,
)
from rapidata.rapidata_client.job.rapidata_job_definition import (
    RapidataJobDefinition,
)
from rapidata.rapidata_client.settings import CustomSetting


def _revision(number: int = 3, **overrides) -> GetJobRevisionEndpointOutput:
    data = {
        "definitionId": "jd-1",
        "revisionNumber": number,
        "state": "Completed",
        "pipelineId": "pip-1",
        "datasetId": "ds-1",
        "aggregatorType": None,
        "workflow": {
            "_t": "SimpleWorkflow",
            "rapid": {
                "_t": "Classify",
                "asset": {"segment": "asset"},
                "title": {"literal": "Which is sharper?"},
                "categories": {
                    "literal": [
                        {"label": "a", "value": "a"},
                        {"label": "b", "value": "b"},
                    ]
                },
            },
            "featureFlags": [{"key": "mute_video_asset", "value": "true"}],
        },
        "referee": {"_t": "NaiveReferee", "totalVotes": 10},
        "featureFlags": [{"key": "mute_video_asset", "value": "true"}],
        "campaignFeatureFlags": [],
        "validationSetId": None,
        "baseRevisionNumber": 2,
        "createdAt": "2026-10-23T12:00:00Z",
        "createdById": "00000000-0000-0000-0000-000000000001",
        "createdByMail": "a@rapidata.ai",
    }
    data.update(overrides)
    model = GetJobRevisionEndpointOutput.from_dict(data)
    assert model is not None
    return model


def _service(revision: GetJobRevisionEndpointOutput) -> MagicMock:
    service = MagicMock()
    service.environment = "rapidata.ai"
    job_api = service.order.job_api
    job_api.job_definition_definition_id_revision_get.return_value = revision
    job_api.job_definition_definition_id_revision_revision_number_get.return_value = (
        revision
    )
    return service


def _loaded(revision: GetJobRevisionEndpointOutput | None = None):
    service = _service(revision or _revision())
    jd = RapidataJobDefinition("jd-1", "Job", service).reload()
    return jd, service


def _sent_body(service: MagicMock, call: int = -1) -> dict:
    post = service.order.job_api.job_definition_definition_id_revision_post
    body = post.call_args_list[call].kwargs["create_job_revision_endpoint_input"]
    # The generated client serializes through to_dict(); assert on the wire shape.
    return json.loads(json.dumps(body.to_dict(), default=str))


def _respond_with(service: MagicMock, *numbers: int) -> None:
    service.order.job_api.job_definition_definition_id_revision_post.side_effect = [
        CreateJobRevisionEndpointOutput(revisionNumber=n, pipelineId="pip-x")
        for n in numbers
    ]


def test_getters_read_the_loaded_revision():
    jd, _ = _loaded()

    assert jd.revision == 3
    assert jd.base_revision == 2
    assert jd.instruction == "Which is sharper?"
    assert jd.answer_options == ["a", "b"]
    assert jd.responses_per_datapoint == 10
    assert jd.validation_set_id is None
    assert jd.dataset_id == "ds-1"
    assert [(s.key, s.target) for s in jd.settings] == [("mute_video_asset", "rapids")]
    assert not jd.has_unsaved_changes


def test_setters_stage_locally_without_a_request():
    jd, service = _loaded()

    jd.instruction = "Which looks real?"

    assert jd.instruction == "Which looks real?"
    assert jd.has_unsaved_changes
    service.order.job_api.job_definition_definition_id_revision_post.assert_not_called()


def test_save_sends_every_field_with_explicit_null_and_base_revision():
    jd, service = _loaded()
    _respond_with(service, 4)

    jd.responses_per_datapoint = 15
    assert jd.save() == 4

    body = _sent_body(service)
    assert set(body) == {
        "workflow",
        "referee",
        "datasetId",
        "rapidFeatureFlags",
        "campaignFeatureFlags",
        "aggregatorType",
        "validationSetId",
        "baseRevisionNumber",
        "requireLatest",
    }
    assert body["validationSetId"] is None
    assert body["aggregatorType"] is None
    assert body["campaignFeatureFlags"] == []
    assert body["baseRevisionNumber"] == 3
    assert body["requireLatest"] is False
    assert body["referee"] == {"_t": "NaiveReferee", "totalVotes": 15}
    assert body["datasetId"] == "ds-1"
    assert body["workflow"]["rapid"]["title"]["literal"] == "Which is sharper?"


def test_save_moves_the_object_to_the_new_revision():
    jd, service = _loaded()
    _respond_with(service, 4)

    jd.validation_set_id = "vs-1"
    jd.save()

    assert jd.revision == 4
    assert not jd.has_unsaved_changes
    service.order.job_api.job_definition_definition_id_revision_revision_number_get.reset_mock()
    jd.instruction  # snapshot is re-read lazily, at the new revision
    service.order.job_api.job_definition_definition_id_revision_revision_number_get.assert_called_once_with(
        definition_id="jd-1", revision_number=4
    )


def test_two_objects_at_the_same_revision_each_send_only_their_own_change():
    a, service = _loaded()
    b = RapidataJobDefinition("jd-1", "Job", service).reload()
    _respond_with(service, 4, 5)

    a.instruction = "Y"
    b.answer_options = ["a", "b", "c"]
    a.save()
    b.save()

    body_a = _sent_body(service, 0)
    body_b = _sent_body(service, 1)
    rapid_a = body_a["workflow"]["rapid"]
    rapid_b = body_b["workflow"]["rapid"]

    assert rapid_a["title"]["literal"] == "Y"
    assert [o["label"] for o in rapid_a["categories"]["literal"]] == ["a", "b"]
    assert rapid_b["title"]["literal"] == "Which is sharper?"
    assert [o["label"] for o in rapid_b["categories"]["literal"]] == ["a", "b", "c"]
    assert body_a["baseRevisionNumber"] == body_b["baseRevisionNumber"] == 3


def test_settings_replace_both_levels():
    jd, service = _loaded()
    _respond_with(service, 4)

    jd.settings = [CustomSetting("k", "v", target="campaign")]
    jd.save()

    body = _sent_body(service)
    assert body["rapidFeatureFlags"] == []
    assert body["campaignFeatureFlags"] == [{"key": "k", "value": "v"}]


def test_require_latest_conflict_raises_and_keeps_changes():
    jd, service = _loaded()
    service.order.job_api.job_definition_definition_id_revision_post.side_effect = (
        RapidataError(
            status_code=409,
            message="conflict",
            details={"title": "Conflict", "latestRevisionNumber": 7},
        )
    )

    jd.instruction = "Y"
    with pytest.raises(RevisionConflictError) as excinfo:
        jd.save(require_latest=True)

    assert excinfo.value.latest_revision == 7
    assert excinfo.value.base_revision == 3
    assert _sent_body(service)["requireLatest"] is True
    assert jd.revision == 3
    assert jd.instruction == "Y"


def test_other_errors_propagate_unchanged():
    jd, service = _loaded()
    error = RapidataError(status_code=400, message="bad")
    service.order.job_api.job_definition_definition_id_revision_post.side_effect = (
        error
    )

    with pytest.raises(RapidataError):
        jd.save()


def test_answer_options_rejected_for_workflows_without_options():
    compare = _revision(
        workflow={
            "_t": "SimpleWorkflow",
            "rapid": {
                "_t": "Compare",
                "asset": {"segment": "asset"},
                "criteria": {"literal": "Which is better?"},
            },
        }
    )
    jd, _ = _loaded(compare)

    assert jd.instruction == "Which is better?"
    assert jd.answer_options is None
    with pytest.raises(ValueError):
        jd.answer_options = ["a", "b"]
    assert not jd.has_unsaved_changes


def test_reload_refuses_unsaved_changes():
    jd, _ = _loaded()
    jd.instruction = "Y"

    with pytest.raises(RuntimeError):
        jd.reload()

    jd.discard_changes().reload()
    assert jd.instruction == "Which is sharper?"


def test_reload_loads_a_specific_revision():
    jd, service = _loaded()

    jd.reload(revision=2)

    service.order.job_api.job_definition_definition_id_revision_revision_number_get.assert_called_with(
        definition_id="jd-1", revision_number=2
    )


def _audience(service: MagicMock) -> RapidataAudienceBase:
    response = MagicMock(job_id="job-1", cost_warning=None)
    response.content_check_skip_denied = None
    service.order.job_api.job_post.return_value = response
    return RapidataAudienceBase(
        id="aud-1", name="Aud", filters=[], openapi_service=service
    )


def test_assign_job_pins_the_objects_revision():
    jd, service = _loaded()
    audience = _audience(service)

    audience.assign_job(jd)

    sent = service.order.job_api.job_post.call_args.kwargs[
        "create_job_endpoint_input"
    ]
    assert sent.revision_number == 3


def test_assign_job_refuses_unsaved_changes():
    jd, service = _loaded()
    audience = _audience(service)
    jd.instruction = "Y"

    with pytest.raises(RuntimeError):
        audience.assign_job(jd)

    service.order.job_api.job_post.assert_not_called()


def test_created_definition_is_at_revision_one_without_a_fetch():
    service = _service(_revision(1))

    jd = RapidataJobDefinition("jd-1", "Job", service, revision=1)

    assert jd.revision == 1
    service.order.job_api.job_definition_definition_id_revision_revision_number_get.assert_not_called()


def test_instruction_setter_enforces_the_length_cap():
    jd, _ = _loaded()

    with pytest.raises(ValueError):
        jd.instruction = "x" * 251
    assert not jd.has_unsaved_changes
