from __future__ import annotations

import copy

import pytest

from scripts.check_adaptive_stopping_contract import (
    audit_schema,
    referee_unions,
    simple_workflows,
)


def _schema() -> dict:
    schemas = {}
    for union, kind in [
        ("IReferee", "AdaptiveStoppingReferee"),
        ("IRefereeConfig", "AdaptiveStoppingRefereeConfig"),
    ]:
        name = f"{union}Adaptive"
        schemas[union] = {"oneOf": [{"$ref": f"#/components/schemas/{name}"}]}
        schemas[name] = {
            "properties": {
                "_t": {"enum": [kind]},
                "maxVotes": {"type": "integer"},
                "minConfidence": {"type": "number"},
                "ambiguityThreshold": {"type": "number"},
                "unsolvableThreshold": {"type": "number"},
                "maxOutcomeCount": {"type": "integer"},
            }
        }
    return {"components": {"schemas": schemas}}


def test_model_suffix_is_not_required_unless_emitted():
    document = _schema()
    assert audit_schema(document) == []
    schemas = document["components"]["schemas"]
    schemas["IRefereeConfigModel"] = copy.deepcopy(schemas["IRefereeConfig"])
    assert audit_schema(document) == []
    assert (
        referee_unions(document)["IRefereeConfigModel"]
        == "AdaptiveStoppingRefereeConfig"
    )


def test_schema_ids_are_discovered_from_emitted_discriminators():
    document = _schema()
    schemas = document["components"]["schemas"]
    schemas["PipelineConfig"] = schemas.pop("IRefereeConfig")
    assert audit_schema(document) == []
    assert referee_unions(document)["PipelineConfig"] == "AdaptiveStoppingRefereeConfig"


@pytest.mark.parametrize("union", ["IReferee", "IRefereeConfig"])
@pytest.mark.parametrize(
    "field",
    [
        "maxVotes",
        "minConfidence",
        "ambiguityThreshold",
        "unsolvableThreshold",
        "maxOutcomeCount",
    ],
)
def test_missing_fields_in_emitted_variants_are_rejected(union, field):
    document = _schema()
    del document["components"]["schemas"][f"{union}Adaptive"]["properties"][field]
    assert audit_schema(document) == [
        f"source {union}: missing canonical fields {field}"
    ]


def test_missing_config_union_is_rejected():
    document = _schema()
    del document["components"]["schemas"]["IRefereeConfig"]
    assert audit_schema(document) == [
        "source: no emitted union for AdaptiveStoppingRefereeConfig"
    ]


def test_inherited_fields_and_const_discriminators_are_supported():
    document = _schema()
    original = copy.deepcopy(
        document["components"]["schemas"]["IRefereeConfigAdaptive"]
    )
    document["components"]["schemas"]["BaseConfig"] = {
        "properties": {
            key: value for key, value in original["properties"].items() if key != "_t"
        }
    }
    document["components"]["schemas"]["IRefereeConfigAdaptive"] = {
        "allOf": [
            {"$ref": "#/components/schemas/BaseConfig"},
            {"properties": {"_t": {"const": "AdaptiveStoppingRefereeConfig"}}},
        ]
    }
    assert audit_schema(document) == []


def test_unresolved_external_schema_is_not_a_joined_source():
    document = _schema()
    document["components"]["schemas"]["IReferee"]["oneOf"][0][
        "$ref"
    ] = "order.openapi.json#/components/schemas/Adaptive"
    assert "provide a joined schema" in audit_schema(document)[0]


def test_workflow_readers_are_checked_only_when_emitted():
    document = _schema()
    assert simple_workflows(document) == {}
    document["components"]["schemas"]["ReturnedWorkflow"] = {
        "properties": {
            "_t": {"const": "SimpleWorkflowModel"},
            "referee": {"$ref": "#/components/schemas/IRefereeConfig"},
        }
    }
    assert simple_workflows(document) == {"ReturnedWorkflow": "SimpleWorkflowModel"}
