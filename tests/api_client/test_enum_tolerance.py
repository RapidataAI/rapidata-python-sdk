from __future__ import annotations

import json

from rapidata.api_client.models.audience_job_state import AudienceJobState
from rapidata.api_client.models.get_job_by_id_endpoint_output import (
    GetJobByIdEndpointOutput,
)


def _job_json(state: str) -> str:
    return json.dumps(
        {
            "jobId": "job-1",
            "name": "My Job",
            "definitionId": "def-1",
            "audienceId": "aud-1",
            "revisionNumber": 1,
            "pipelineId": "pip-1",
            "campaignId": "cmp-1",
            "audienceName": "My Audience",
            "state": state,
            "isPublic": False,
            "audienceDeleted": False,
            "createdAt": "2026-10-05T00:00:00Z",
            "ownerId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "ownerMail": "owner@example.com",
            "organizationId": "org-1",
        }
    )


def test_known_value_resolves_to_its_member():
    job = GetJobByIdEndpointOutput.from_json(_job_json("Blocked"))

    assert job is not None
    assert job.state is AudienceJobState.BLOCKED


def test_value_unknown_to_this_client_still_parses():
    job = GetJobByIdEndpointOutput.from_json(_job_json("SomeFutureState"))

    assert job is not None
    assert isinstance(job.state, AudienceJobState)
    assert job.state.value == "SomeFutureState"
    assert job.state == "SomeFutureState"
    assert job.state not in (AudienceJobState.COMPLETED, AudienceJobState.FAILED)
