"""Fewer than 10 responses per datapoint needs the LowResponseCount capability, checked before any upload."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.get_job_revision_endpoint_output import (
    GetJobRevisionEndpointOutput,
)
from rapidata.rapidata_client.exceptions import LowResponseCountError, RapidataError
from rapidata.rapidata_client.job._response_minimum import (
    ensure_response_count_allowed,
)
from rapidata.rapidata_client.job.rapidata_job_definition import (
    RapidataJobDefinition,
)
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager

SIMPLE = MagicMock(to_dict=lambda: {"_t": "SimpleWorkflow"})
RANKING = MagicMock(to_dict=lambda: {"_t": "GroupedRankingWorkflow"})


def _service(userinfo: dict | Exception, status: int = 200) -> MagicMock:
    service = MagicMock()
    service.environment = "rapidata.ai"
    if isinstance(userinfo, Exception):
        service.api_client.call_api.side_effect = userinfo
    else:
        response = MagicMock(status=status)
        response.read.return_value = json.dumps(userinfo).encode()
        service.api_client.call_api.return_value = response
    return service


@pytest.mark.parametrize(
    "responses, workflow, userinfo, status, raises, lookups",
    [
        (10, SIMPLE, {}, 200, False, 0),
        (9, SIMPLE, {}, 200, True, 1),
        (9, SIMPLE, {"capabilities": ["Faucets", "LowResponseCount"]}, 200, False, 1),
        (9, SIMPLE, {"capabilities": "LowResponseCount"}, 200, False, 1),
        (9, SIMPLE, {"platform_relations": ["admin"]}, 200, False, 1),
        (9, SIMPLE, RuntimeError("timeout"), 200, False, 1),
        (9, SIMPLE, {}, 401, False, 1),
        (1, RANKING, {}, 200, False, 0),
    ],
    ids=[
        "at-minimum",
        "not-granted",
        "granted",
        "granted-single-claim",
        "platform-admin",
        "lookup-error-fails-open",
        "lookup-non-200-fails-open",
        "ranking-not-gated",
    ],
)
def test_gate(responses, workflow, userinfo, status, raises, lookups):
    service = _service(userinfo, status)

    if raises:
        with pytest.raises(LowResponseCountError) as error:
            ensure_response_count_allowed(service, workflow, responses)
        assert "Requested 9 responses per datapoint (minimum 10)" in str(error.value)
        assert "email info@rapidata.ai with your use case" in str(error.value)
    else:
        ensure_response_count_allowed(service, workflow, responses)

    assert service.api_client.call_api.call_count == lookups


def test_grant_is_cached_per_client():
    service = _service({"capabilities": ["LowResponseCount"]})

    ensure_response_count_allowed(service, SIMPLE, 3)
    ensure_response_count_allowed(service, SIMPLE, 3)

    assert service.api_client.call_api.call_count == 1


def test_create_raises_before_any_upload():
    service = _service({})

    with pytest.raises(LowResponseCountError):
        RapidataJobManager(service).create_classification_job_definition(
            name="Job",
            instruction="Is this a cat?",
            answer_options=["yes", "no"],
            datapoints=["https://example.com/a.jpg"],
            responses_per_datapoint=5,
        )

    service.dataset.dataset_api.dataset_post.assert_not_called()


def test_revision_setter_raises():
    service = _service({})
    revision = GetJobRevisionEndpointOutput.from_dict(
        {
            "definitionId": "jd-1",
            "revisionNumber": 1,
            "state": "Completed",
            "pipelineId": "pip-1",
            "datasetId": "ds-1",
            "workflow": {
                "_t": "SimpleWorkflow",
                "rapid": {
                    "_t": "FreeText",
                    "asset": {"segment": "asset"},
                    "question": {"literal": "Describe it"},
                },
            },
            "referee": {"_t": "NaiveReferee", "totalVotes": 10},
            "featureFlags": [],
            "campaignFeatureFlags": [],
            "createdAt": "2026-10-23T12:00:00Z",
            "createdById": "00000000-0000-0000-0000-000000000001",
            "createdByMail": "a@rapidata.ai",
        }
    )
    service.order.job_api.job_definition_definition_id_revision_get.return_value = (
        revision
    )
    jd = RapidataJobDefinition("jd-1", "Job", service).reload()

    with pytest.raises(LowResponseCountError):
        jd.responses_per_datapoint = 5

    assert not jd.has_unsaved_changes


def test_validation_errors_render_one_line_per_message():
    error = RapidataError(
        status_code=400,
        details={
            "title": "One or more validation errors occurred.",
            "errors": {"Referee": ["At least 10 responses.", "Second."], "": "Top."},
        },
        trace_id="abc",
    )

    assert str(error).splitlines()[:5] == [
        "One or more validation errors occurred.",
        "Referee: At least 10 responses.",
        "Referee: Second.",
        "Top.",
        "Trace Id: abc",
    ]
