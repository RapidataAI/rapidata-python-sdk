from __future__ import annotations

import copy

import pytest

from scripts.check_adaptive_stopping_contract import audit_schema


def _schema() -> dict:
    schemas = {}
    for union, kind in [
        ("IReferee", "AdaptiveStoppingReferee"),
        ("IRefereeConfig", "AdaptiveStoppingRefereeConfig"),
        ("IRefereeConfigModel", "AdaptiveStoppingRefereeConfig"),
    ]:
        name = f"{union}Adaptive"
        schemas[union] = {"oneOf": [{"$ref": f"#/components/schemas/{name}"}]}
        schemas[name] = {
            "type": "object",
            "properties": {
                "_t": {"type": "string", "enum": [kind]},
                "maxVotes": {"type": "integer", "default": 100},
                "minConfidence": {"type": "number", "default": 0.9},
                "ambiguityThreshold": {"type": "number", "default": 0.64},
                "unsolvableThreshold": {"type": "number", "default": 0.5},
                "maxOutcomeCount": {"type": "integer", "default": 1},
            },
        }
    return {"openapi": "3.1.0", "components": {"schemas": schemas}}


def test_all_three_canonical_unions_must_be_present():
    document = _schema()
    assert audit_schema(document) == []
    del document["components"]["schemas"]["IRefereeConfigModel"]
    assert len(audit_schema(document)) == 1
    assert "IRefereeConfigModel" in audit_schema(document)[0]


@pytest.mark.parametrize("union", ["IReferee", "IRefereeConfig", "IRefereeConfigModel"])
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
def test_schema_rejects_each_missing_field_even_if_sdk_adapter_would_fill_it(
    union, field
):
    document = _schema()
    del document["components"]["schemas"][f"{union}Adaptive"]["properties"][field]
    assert audit_schema(document) == [
        f"source {union}: missing canonical fields {field}"
    ]


def test_discriminator_ownership_is_checked():
    document = _schema()
    document["components"]["schemas"]["IRefereeConfigAdaptive"]["properties"]["_t"][
        "enum"
    ] = ["AdaptiveStoppingReferee"]
    assert audit_schema(document) == [
        "source IRefereeConfig: expected one AdaptiveStoppingRefereeConfig variant, found 0"
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


def test_unresolved_external_schema_is_not_a_valid_joined_source():
    document = _schema()
    document["components"]["schemas"]["IReferee"]["oneOf"][0][
        "$ref"
    ] = "order.openapi.json#/components/schemas/Adaptive"
    errors = audit_schema(document)
    assert len(errors) == 1
    assert "provide a joined schema" in errors[0]
