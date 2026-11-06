from __future__ import annotations

from functools import lru_cache
from typing import Any, TypeVar, cast

from pydantic import ConfigDict

from rapidata.api_client.lazy_model import LazyValidatedModel

Model = TypeVar("Model", bound=LazyValidatedModel)
_COMPARE_CONTROLS = ("allowBothGood", "allowBothBad", "allowCantSolve")
_CLASSIFY_CONTROLS = ("allowCantSolve",)
_CONTROLS_BY_KIND = {
    "Compare": _COMPARE_CONTROLS,
    "ComparePayload": _COMPARE_CONTROLS,
    "CompareBlueprint": _COMPARE_CONTROLS,
    "Classify": _CLASSIFY_CONTROLS,
    "ClassifyPayload": _CLASSIFY_CONTROLS,
    "ClassifyBlueprint": _CLASSIFY_CONTROLS,
}


def validate_answer_control(name: str, value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a bool")


def compare_outcome_count(rapid: dict[str, Any]) -> int:
    return (
        2 + (rapid.get("allowBothGood") is True) + (rapid.get("allowBothBad") is True)
    )


@lru_cache(maxsize=None)
def _adapter_type(model_type: type[Model]) -> type[Model]:
    return cast(
        type[Model],
        type(
            f"_AnswerControls{model_type.__name__}",
            (model_type,),
            {"model_config": ConfigDict(extra="allow"), "__module__": __name__},
        ),
    )


def with_answer_controls(model: Model, controls: dict[str, bool]) -> Model:
    for name, value in controls.items():
        validate_answer_control(name, value)
    model_type = type(model)
    aliases = {
        field.alias or name: name for name, field in model_type.model_fields.items()
    }
    target = (
        model_type if controls.keys() <= aliases.keys() else _adapter_type(model_type)
    )
    values = {
        name: value
        for name, value in model.__dict__.items()
        if name in model_type.model_fields
    }
    values.update(model.model_extra or {})
    values.update({aliases.get(name, name): value for name, value in controls.items()})
    fields_set = model.model_fields_set | {aliases.get(name, name) for name in controls}
    adapted = target.model_construct(_fields_set=fields_set, **values)
    object.__setattr__(
        adapted,
        "_field_validation_errors",
        getattr(model, "_field_validation_errors", {}),
    )
    return cast(Model, adapted)


def adapt_answer_controls(model_type: type[Model], data: Any) -> Model | None:
    """Retain confirmed controls until the generated leaf declares them."""
    if not isinstance(data, dict):
        return None
    kind = data.get("_t")
    names = _CONTROLS_BY_KIND.get(kind, ()) if isinstance(kind, str) else ()
    controls = {name: data[name] for name in names if name in data}
    aliases = {field.alias or name for name, field in model_type.model_fields.items()}
    if not controls or controls.keys() <= aliases:
        return None
    from_dict = getattr(model_type, "from_dict")
    parsed = from_dict(
        {key: value for key, value in data.items() if key not in controls}
    )
    return with_answer_controls(parsed, controls)
