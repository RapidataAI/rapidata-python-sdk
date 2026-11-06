from __future__ import annotations

import copy
import json

import pytest

from rapidata.api_client.api_client import ApiClient
from rapidata.api_client.models.get_pipeline_by_id_endpoint_output import (
    GetPipelineByIdEndpointOutput,
)

_DEFAULTS = {
    "_t": "AdaptiveStoppingRefereeConfig",
    "maxVotes": 100,
    "minConfidence": 0.9,
    "ambiguityThreshold": 0.64,
    "unsolvableThreshold": 0.5,
    "maxOutcomeCount": 1,
}
_CUSTOM = {
    **_DEFAULTS,
    "maxVotes": 47,
    "minConfidence": 0.95,
    "ambiguityThreshold": 0.73,
    "unsolvableThreshold": 0.6,
    "maxOutcomeCount": 3,
}


def _pipeline(config: dict, kind: str) -> dict:
    blueprint = {"_t": f"{kind}Blueprint", "allowCantSolve": False}
    if kind == "Compare":
        blueprint.update(
            criteria="Which response is better?",
            indexIdentifiers=["Left", "Right"],
            allowBothGood=True,
            allowBothBad=True,
        )
    else:
        values = ["dotted.value", "雪☃️", "arbitrary/value", "bothBad", "c0", "a0"]
        blueprint.update(
            title="Which category fits?",
            categories=[
                {"label": label, "value": value}
                for label, value in zip(reversed(values), values)
            ],
        )
    return {
        "artifacts": {
            "dataset": {
                "_t": "DatasetArtifactModel",
                "datasetId": "dataset-1",
                "identifier": "input-dataset",
            },
            "workflowConfig": {
                "_t": "WorkflowConfigArtifactModel",
                "identifier": "labeling-config",
                "workflowConfig": {
                    "_t": "SimpleWorkflowConfig",
                    "blueprint": blueprint,
                    "referee": copy.deepcopy(config),
                    "featureFlags": [],
                },
            },
            "workflow": {
                "_t": "WorkflowArtifactModel",
                "workflowId": "workflow-1",
                "identifier": "labeling-workflow",
            },
        },
        "featureFlags": [],
    }


@pytest.mark.parametrize("model_type", [GetPipelineByIdEndpointOutput])
@pytest.mark.parametrize("kind", ["Compare", "Classify"])
@pytest.mark.parametrize(
    "config,expected",
    [
        ({"_t": "AdaptiveStoppingRefereeConfig"}, _DEFAULTS),
        (_CUSTOM, _CUSTOM),
        ({"_t": "AdaptiveStoppingRefereeConfig", "ambiguityRange": 0.6}, _DEFAULTS),
        (
            {"_t": "AdaptiveStoppingRefereeConfig", "ambiguityRange": 0.3},
            {**_DEFAULTS, "ambiguityThreshold": 0.91},
        ),
        ({**_CUSTOM, "ambiguityRange": "ignored legacy value"}, _CUSTOM),
    ],
    ids=["defaults", "custom", "legacy-.6", "legacy-.3", "canonical-precedence"],
)
def test_complete_pipeline_config_roundtrip_keeps_owning_discriminator_and_resolved_values(
    model_type, kind, config, expected
):
    wire = _pipeline(config, kind)
    original = copy.deepcopy(wire)
    model = model_type.from_json(json.dumps(wire))
    artifact = model.artifacts["workflowConfig"].actual_instance
    workflow = artifact.workflow_config.actual_instance
    for part in [
        model,
        artifact,
        workflow,
        workflow.blueprint.actual_instance,
        workflow.referee,
    ]:
        assert not getattr(part, "_field_validation_errors", {})
    assert workflow.referee.to_dict() == expected
    assert workflow.blueprint.to_dict()["allowCantSolve"] is False
    assert (
        workflow.referee.to_dict()["unsolvableThreshold"]
        == expected["unsolvableThreshold"]
    )
    with ApiClient() as client:
        encoded = client.sanitize_for_serialization(model)
    for output in [model.to_dict(), json.loads(model.to_json()), encoded]:
        exported = output["artifacts"]["workflowConfig"]["workflowConfig"]
        assert exported["referee"] == expected
        original_blueprint = wire["artifacts"]["workflowConfig"]["workflowConfig"][
            "blueprint"
        ]
        assert {
            key: exported["blueprint"][key] for key in original_blueprint
        } == original_blueprint
        assert "ambiguityRange" not in exported["referee"]
        assert exported["referee"]["_t"] == "AdaptiveStoppingRefereeConfig"
    assert wire == original
    reloaded = model_type.from_dict(encoded)
    assert (
        reloaded.artifacts[
            "workflowConfig"
        ].actual_instance.workflow_config.actual_instance.referee.to_dict()
        == expected
    )
