from __future__ import annotations

import math
import json

import pytest
from pydantic import Field

from rapidata import AdaptiveStopping
from rapidata.api_client.api_client import ApiClient
from rapidata.api_client.lazy_model import LazyValidatedModel
from rapidata.api_client.models.create_job_definition_endpoint_input import (
    CreateJobDefinitionEndpointInput,
)
from rapidata.api_client.models.i_referee import IReferee
from rapidata.api_client.models.feature_flag import FeatureFlag
from rapidata.api_client.models.i_referee_config import IRefereeConfig
from rapidata.api_client.models.i_referee_config_model import IRefereeConfigModel
from rapidata.api_client.models.i_workflow_config import IWorkflowConfig
from rapidata.api_client.models.i_workflow_model import IWorkflowModel
from rapidata.rapidata_client.referee import _adaptive_stopping_adapter as adapter
from rapidata.rapidata_client.workflow import CompareWorkflow


CANONICAL_CONFIG = {
    "_t": "AdaptiveStoppingRefereeConfig",
    "maxVotes": 100,
    "minConfidence": 0.9,
    "ambiguityThreshold": 0.64,
    "unsolvableThreshold": 0.5,
    "maxOutcomeCount": 1,
}


def test_public_defaults_write_resolved_workflow_config():
    config = AdaptiveStopping()

    assert config.ambiguity_threshold == 0.64
    assert config.max_outcome_count == 1
    assert config.unsolvable_threshold == 0.5
    assert config._to_referee()._to_dict() == CANONICAL_CONFIG
    assert AdaptiveStopping._from_dict(CANONICAL_CONFIG) == config
    assert AdaptiveStopping._from_dict({}) == config


def test_nondefault_settings_survive_workflow_config_roundtrip():
    config = AdaptiveStopping(
        min_confidence=0.95,
        ambiguity_threshold=0.73,
        max_responses=47,
        max_outcome_count=3,
        unsolvable_threshold=0.6,
    )

    wire = config._to_referee()._to_dict()

    assert wire == {
        "_t": "AdaptiveStoppingRefereeConfig",
        "maxVotes": 47,
        "minConfidence": 0.95,
        "ambiguityThreshold": 0.73,
        "unsolvableThreshold": 0.6,
        "maxOutcomeCount": 3,
    }
    assert AdaptiveStopping._from_dict(wire) == config


@pytest.mark.parametrize(
    "legacy_range, threshold", [(0.6, 0.64), (0.5, 0.75), (0.3, 0.91)]
)
def test_legacy_range_reads_as_normalized_threshold_and_never_writes(
    legacy_range, threshold
):
    config = AdaptiveStopping._from_dict(
        {"_t": "AdaptiveStoppingRefereeConfig", "ambiguityRange": legacy_range}
    )

    wire = config._to_referee()._to_dict()

    assert config.ambiguity_threshold == pytest.approx(threshold)
    assert wire["ambiguityThreshold"] == pytest.approx(threshold)
    assert "ambiguityRange" not in wire
    assert wire["unsolvableThreshold"] == 0.5


def test_canonical_threshold_takes_precedence_over_legacy_range():
    wire = {**CANONICAL_CONFIG, "ambiguityThreshold": 0.8, "ambiguityRange": 0.6}
    assert AdaptiveStopping._from_dict(wire).ambiguity_threshold == 0.8


@pytest.mark.parametrize(
    "field", ["min_confidence", "ambiguity_threshold", "unsolvable_threshold"]
)
@pytest.mark.parametrize(
    "value", [0, 1, -0.1, 1.1, True, False, None, math.nan, math.inf, -math.inf, "0.5"]
)
def test_confidence_thresholds_reject_invalid_values(field, value):
    with pytest.raises(ValueError, match=field):
        AdaptiveStopping(**{field: value})


@pytest.mark.parametrize("field", ["max_responses", "max_outcome_count"])
@pytest.mark.parametrize(
    "value", [0, -1, 1.5, True, False, None, math.nan, math.inf, "3"]
)
def test_counts_require_positive_integers(field, value):
    with pytest.raises(ValueError, match=field):
        AdaptiveStopping(**{field: value})


@pytest.mark.parametrize("value", [0, 1, True, None, math.nan, "0.6"])
def test_invalid_legacy_range_is_not_silently_defaulted(value):
    with pytest.raises(ValueError, match="ambiguityRange"):
        AdaptiveStopping._from_dict({"ambiguityRange": value})


def test_null_resolved_threshold_does_not_mean_disabled_cant_solve():
    with pytest.raises(ValueError, match="unsolvable_threshold"):
        AdaptiveStopping._from_dict({**CANONICAL_CONFIG, "unsolvableThreshold": None})


def test_unmerged_range_keyword_is_replaced():
    with pytest.raises(TypeError, match="ambiguity_range"):
        AdaptiveStopping(ambiguity_range=0.6)


@pytest.mark.parametrize("union", [IReferee, IRefereeConfig, IRefereeConfigModel])
def test_union_json_and_pydantic_serialization_keep_canonical_settings(union):
    wire = {
        **CANONICAL_CONFIG,
        "_t": (
            "AdaptiveStoppingReferee"
            if union is IReferee
            else "AdaptiveStoppingRefereeConfig"
        ),
    }
    model = union.from_json(json.dumps(wire))
    assert model.to_dict() == wire
    assert json.loads(model.to_json()) == wire
    assert model.model_dump(by_alias=True) == wire


def test_create_request_http_serializer_preserves_all_five_settings():
    config = AdaptiveStopping(
        min_confidence=0.95,
        ambiguity_threshold=0.73,
        max_responses=47,
        max_outcome_count=3,
        unsolvable_threshold=0.6,
    )
    body = CreateJobDefinitionEndpointInput(
        definitionName="Job",
        datasetId="dataset-1",
        workflow=CompareWorkflow(instruction="Which?")._to_model(),
        referee=config._to_referee()._to_model(),
        rapidFeatureFlags=[FeatureFlag(key="compare_unsure", value="5000")],
    )
    expected = {**config._to_referee()._to_dict(), "_t": "AdaptiveStoppingReferee"}
    with ApiClient() as client:
        assert client.sanitize_for_serialization(body)["referee"] == expected
    assert body.to_dict()["referee"] == expected
    assert json.loads(body.to_json())["referee"] == expected


@pytest.mark.parametrize("read_model", [False, True])
def test_nested_workflow_referee_config_roundtrips(read_model):
    blueprint = {
        "_t": "CompareBlueprint",
        "criteria": "Which?",
        "indexIdentifiers": ["A", "B"],
    }
    if read_model:
        wire = {
            "_t": "SimpleWorkflowModel",
            "id": "workflow-1",
            "state": "Created",
            "blueprint": blueprint,
            "referee": CANONICAL_CONFIG,
            "name": "Job",
            "ownerMail": None,
        }
        model = IWorkflowModel.from_dict(wire)
    else:
        wire = {
            "_t": "SimpleWorkflowConfig",
            "blueprint": blueprint,
            "referee": CANONICAL_CONFIG,
            "featureFlags": [],
        }
        model = IWorkflowConfig.from_dict(wire)
    assert model.to_dict()["referee"] == CANONICAL_CONFIG
    assert json.loads(model.to_json())["referee"] == CANONICAL_CONFIG


def test_adapter_defers_to_native_canonical_variants_after_regeneration(monkeypatch):
    class NativeVariant(LazyValidatedModel):
        max_votes: int = Field(alias="maxVotes")
        min_confidence: float = Field(alias="minConfidence")
        ambiguity_threshold: float = Field(alias="ambiguityThreshold")
        unsolvable_threshold: float = Field(alias="unsolvableThreshold")
        max_outcome_count: int = Field(alias="maxOutcomeCount")

    class NativeUnion(LazyValidatedModel):
        actual_instance: NativeVariant | None = None

    monkeypatch.setitem(
        adapter._ADAPTERS,
        NativeUnion,
        ("AdaptiveStoppingRefereeConfig", adapter._AdaptiveRefereeConfig),
    )
    assert adapter.adapt_referee_model(NativeUnion, CANONICAL_CONFIG) is None
