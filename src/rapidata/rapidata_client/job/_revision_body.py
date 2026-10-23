from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from rapidata.api_client.models.create_job_revision_endpoint_input import (
    CreateJobRevisionEndpointInput,
)
from rapidata.api_client.models.i_order_workflow_input import IOrderWorkflowInput
from rapidata.api_client.models.i_referee import IReferee

if TYPE_CHECKING:
    from rapidata.api_client.models.feature_flag import FeatureFlag
    from rapidata.api_client.models.get_job_revision_endpoint_output import (
        GetJobRevisionEndpointOutput,
    )
    from rapidata.rapidata_client.settings import RapidataSetting

_INSTRUCTION_FIELD_BY_RAPID = {
    "Classify": "title",
    "Transcription": "title",
    "Compare": "criteria",
    "FreeText": "question",
    "BoundingBox": "target",
    "Line": "target",
    "Locate": "target",
    "NamedEntity": "target",
    "Polygon": "target",
    "Scrub": "target",
}

_VOTES_FIELD_BY_REFEREE = {
    "NaiveReferee": "totalVotes",
    "QuorumReferee": "maxVotes",
    "EarlyStoppingReferee": "maxVotes",
}


def _as_dict(model: IOrderWorkflowInput | IReferee) -> dict[str, Any]:
    return cast(dict[str, Any], model.to_dict())


def _workflow_kind(workflow: dict[str, Any]) -> str:
    if workflow.get("_t") == "SimpleWorkflow":
        return (workflow.get("rapid") or {}).get("_t", "SimpleWorkflow")
    return workflow.get("_t", "")


def _get_instruction(workflow: IOrderWorkflowInput) -> str | None:
    data = _as_dict(workflow)
    if data.get("_t") == "GroupedRankingWorkflow":
        return data.get("criteria")
    field = _INSTRUCTION_FIELD_BY_RAPID.get(_workflow_kind(data))
    if data.get("_t") != "SimpleWorkflow" or field is None:
        return None
    binding = data["rapid"].get(field) or {}
    return binding.get("literal")


def _with_instruction(workflow: IOrderWorkflowInput, text: str) -> IOrderWorkflowInput:
    data = _as_dict(workflow)
    if data.get("_t") == "GroupedRankingWorkflow":
        data["criteria"] = text
    elif data.get("_t") == "SimpleWorkflow" and (
        field := _INSTRUCTION_FIELD_BY_RAPID.get(_workflow_kind(data))
    ):
        data["rapid"][field] = {"literal": text}
    else:
        raise ValueError(
            f"A '{_workflow_kind(data)}' job definition has no instruction to change."
        )
    return IOrderWorkflowInput.from_dict(data)  # type: ignore[return-value]


def _get_answer_options(workflow: IOrderWorkflowInput) -> list[str] | None:
    data = _as_dict(workflow)
    if _workflow_kind(data) != "Classify":
        return None
    literal = (data["rapid"].get("categories") or {}).get("literal")
    return [option["label"] for option in literal] if literal else None


def _with_answer_options(
    workflow: IOrderWorkflowInput, options: list[str]
) -> IOrderWorkflowInput:
    data = _as_dict(workflow)
    if _workflow_kind(data) != "Classify":
        raise ValueError(
            f"A '{_workflow_kind(data)}' job definition has no answer options; "
            "only classification job definitions do."
        )
    data["rapid"]["categories"] = {
        "literal": [{"label": option, "value": option} for option in options]
    }
    return IOrderWorkflowInput.from_dict(data)  # type: ignore[return-value]


def _get_responses(referee: IReferee) -> int:
    data = _as_dict(referee)
    field = _VOTES_FIELD_BY_REFEREE.get(data.get("_t", ""))
    if field is None:
        raise ValueError(
            f"A '{data.get('_t')}' referee has no responses per datapoint."
        )
    return data[field]


def _with_responses(referee: IReferee, responses: int) -> IReferee:
    data = _as_dict(referee)
    field = _VOTES_FIELD_BY_REFEREE.get(data.get("_t", ""))
    if field is None:
        raise ValueError(
            f"A '{data.get('_t')}' referee has no responses per datapoint to change."
        )
    data[field] = responses
    return IReferee.from_dict(data)  # type: ignore[return-value]


def _split_settings(
    settings: list[RapidataSetting],
) -> tuple[list[FeatureFlag], list[FeatureFlag]]:
    rapid = [s._to_feature_flag() for s in settings if s.target == "rapids"]
    campaign = [s._to_feature_flag() for s in settings if s.target == "campaign"]
    return rapid, campaign


def _full_body(
    snapshot: GetJobRevisionEndpointOutput,
    pending: dict[str, Any],
    require_latest: bool,
) -> CreateJobRevisionEndpointInput:
    workflow = snapshot.workflow
    if "instruction" in pending:
        workflow = _with_instruction(workflow, pending["instruction"])
    if "answer_options" in pending:
        workflow = _with_answer_options(workflow, pending["answer_options"])

    referee = snapshot.referee
    if "responses_per_datapoint" in pending:
        referee = _with_responses(referee, pending["responses_per_datapoint"])

    if "settings" in pending:
        rapid_flags, campaign_flags = _split_settings(pending["settings"])
    else:
        rapid_flags = list(snapshot.feature_flags)
        campaign_flags = list(snapshot.campaign_feature_flags)

    # Every field is passed explicitly: the server inherits any field left out
    # from the latest revision, and a None validationSetId must go out as null.
    return CreateJobRevisionEndpointInput(
        workflow=workflow,
        referee=referee,
        datasetId=pending.get("dataset_id", snapshot.dataset_id),
        rapidFeatureFlags=rapid_flags,
        campaignFeatureFlags=campaign_flags,
        aggregatorType=snapshot.aggregator_type,
        validationSetId=pending.get("validation_set_id", snapshot.validation_set_id),
        baseRevisionNumber=snapshot.revision_number,
        requireLatest=require_latest,
    )


def _required_segments(workflow: IOrderWorkflowInput) -> set[str]:
    from rapidata.rapidata_client.datapoints._default_segments import (
        ANSWER_OPTIONS_SEGMENT_KEY,
        TRANSCRIPTION_SEGMENT_KEY,
    )

    rapid = _as_dict(workflow).get("rapid") or {}
    bound = {
        str(value.get("segment")) for value in rapid.values() if isinstance(value, dict)
    }
    return bound & {ANSWER_OPTIONS_SEGMENT_KEY, TRANSCRIPTION_SEGMENT_KEY}
