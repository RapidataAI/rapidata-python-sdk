from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

_UNIONS = {
    "IReferee": "AdaptiveStoppingReferee",
    "IRefereeConfig": "AdaptiveStoppingRefereeConfig",
    "IRefereeConfigModel": "AdaptiveStoppingRefereeConfig",
}
_DEFAULTS = {
    "maxVotes": 100,
    "minConfidence": 0.9,
    "ambiguityThreshold": 0.64,
    "unsolvableThreshold": 0.5,
    "maxOutcomeCount": 1,
}


def _expand(
    document: dict[str, Any], schema: dict[str, Any], seen: frozenset[str] = frozenset()
) -> dict[str, Any]:
    parts = []
    if ref := schema.get("$ref"):
        if not ref.startswith("#/") or ref in seen:
            raise ValueError(
                f"unresolved or cyclic reference {ref}; provide a joined schema"
            )
        target = document
        for key in ref[2:].split("/"):
            target = target[key.replace("~1", "/").replace("~0", "~")]
        parts.append(_expand(document, target, seen | {ref}))
    parts.extend(_expand(document, part, seen) for part in schema.get("allOf", []))
    parts.append(schema)
    result: dict[str, Any] = {}
    properties: dict[str, Any] = {}
    for part in parts:
        result.update(part)
        properties.update(part.get("properties", {}))
    result["properties"] = properties
    return result


def audit_schema(document: dict[str, Any]) -> list[str]:
    errors = []
    schemas = document.get("components", {}).get("schemas", {})
    for name, discriminator in _UNIONS.items():
        try:
            union = _expand(document, schemas[name])
            variants = [
                _expand(document, item)
                for item in union.get("oneOf", union.get("anyOf", []))
            ]
            matching = [
                variant
                for variant in variants
                if discriminator in variant["properties"].get("_t", {}).get("enum", [])
                or variant["properties"].get("_t", {}).get("const") == discriminator
            ]
            if len(matching) != 1:
                errors.append(
                    f"source {name}: expected one {discriminator} variant, found {len(matching)}"
                )
                continue
            missing = _DEFAULTS.keys() - matching[0]["properties"].keys()
            if missing:
                errors.append(
                    f"source {name}: missing canonical fields {', '.join(sorted(missing))}"
                )
        except (KeyError, TypeError, ValueError) as error:
            errors.append(f"source {name}: {error}")
    return errors


def audit_generated() -> list[str]:
    from rapidata.api_client.api_client import ApiClient
    from rapidata.api_client.models.i_referee import IReferee
    from rapidata.api_client.models.i_referee_config import IRefereeConfig
    from rapidata.api_client.models.i_referee_config_model import IRefereeConfigModel
    from rapidata.api_client.models.i_workflow_config import IWorkflowConfig
    from rapidata.api_client.models.i_workflow_model import IWorkflowModel

    errors = []
    models = [IReferee, IRefereeConfig, IRefereeConfigModel]
    # A fallback adapter must not hide omissions from the branch-built schema.
    with patch(
        "rapidata.rapidata_client.referee._adaptive_stopping_adapter.adapt_referee_model",
        return_value=None,
    ):
        for model_type in models:
            name = model_type.__name__
            expected = {"_t": _UNIONS[name], **_DEFAULTS}
            try:
                parsed = model_type.from_dict(expected)
                actual = parsed.actual_instance
                aliases = {
                    field.alias or key
                    for key, field in type(actual).model_fields.items()
                }
                missing = _DEFAULTS.keys() - aliases
                if missing:
                    raise ValueError(
                        f"native variant lacks {', '.join(sorted(missing))}"
                    )
                custom = {
                    **expected,
                    "maxVotes": 47,
                    "minConfidence": 0.95,
                    "ambiguityThreshold": 0.73,
                    "unsolvableThreshold": 0.6,
                    "maxOutcomeCount": 3,
                }
                for incoming, outgoing in [
                    (expected, expected),
                    (custom, custom),
                    ({"_t": _UNIONS[name]}, expected),
                    (
                        {"_t": _UNIONS[name], "ambiguityRange": 0.3},
                        {**expected, "ambiguityThreshold": 0.91},
                    ),
                    ({**expected, "ambiguityRange": "ignored"}, expected),
                ]:
                    instance = model_type.from_dict(incoming)
                    invalid = getattr(
                        instance.actual_instance, "_field_validation_errors", {}
                    )
                    if invalid:
                        raise ValueError(
                            f"native fields failed validation: {', '.join(sorted(invalid))}"
                        )
                    with ApiClient() as client:
                        if client.sanitize_for_serialization(instance) != outgoing:
                            raise ValueError(
                                "native HTTP serialization changed the resolved contract"
                            )
                    if json.loads(instance.to_json()) != outgoing:
                        raise ValueError(
                            "native JSON round-trip changed the resolved contract"
                        )
            except (AttributeError, TypeError, ValueError) as error:
                errors.append(f"generated {name}: {error}")
        config = {"_t": "AdaptiveStoppingRefereeConfig", **_DEFAULTS}
        blueprint = {
            "_t": "CompareBlueprint",
            "criteria": "Which?",
            "indexIdentifiers": ["A", "B"],
        }
        for model_type, wire in [
            (
                IWorkflowConfig,
                {
                    "_t": "SimpleWorkflowConfig",
                    "blueprint": blueprint,
                    "referee": config,
                    "featureFlags": [],
                },
            ),
            (
                IWorkflowModel,
                {
                    "_t": "SimpleWorkflowModel",
                    "id": "workflow-1",
                    "state": "Created",
                    "blueprint": blueprint,
                    "referee": config,
                    "name": "Job",
                    "ownerMail": None,
                },
            ),
        ]:
            try:
                model = model_type.from_dict(wire)
                if model.to_dict()["referee"] != config:
                    raise ValueError(
                        "native workflow referee did not retain all five config fields"
                    )
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                errors.append(f"generated {model_type.__name__}: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate adaptive referee unions in branch-built OpenAPI and generated models."
    )
    parser.add_argument(
        "schema", type=Path, help="Joined backend OpenAPI document used for generation"
    )
    parser.add_argument(
        "--check-generated",
        action="store_true",
        help="Require native support without the compatibility adapter",
    )
    args = parser.parse_args()
    errors = audit_schema(json.loads(args.schema.read_text()))
    if not errors and args.check_generated:
        errors.extend(audit_generated())
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(
        "Adaptive contract verified in all three unions"
        + (" and native workflow models" if args.check_generated else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
