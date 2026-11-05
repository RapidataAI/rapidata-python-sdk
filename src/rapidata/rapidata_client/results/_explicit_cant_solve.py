from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional, TypeVar, cast

from pydantic import (
    BaseModel,
    Field,
    StrictBool,
    StrictStr,
    ValidationError,
    create_model,
)

from rapidata.api_client.lazy_model import LazyValidatedModel

Model = TypeVar("Model", bound=BaseModel)


@lru_cache(maxsize=None)
def _response_type(model_type: type[Model], empty_category: bool) -> type[Model]:
    fields: dict[str, Any] = {
        "cant_solve": (StrictBool, Field(default=False, alias="cantSolve"))
    }
    if empty_category:
        fields["category"] = (Optional[StrictStr], None)
    return cast(
        type[Model],
        create_model(
            f"_ExplicitCantSolve{model_type.__name__}{'EmptyCategory' if empty_category else ''}",
            __base__=model_type,
            __module__=__name__,
            **fields,
        ),
    )


def adapt_response_model(model_type: type[Model], data: Any) -> Model | None:
    """Retain the explicit CS marker until generated responses declare it."""
    if not isinstance(data, dict):
        return None
    kind = data.get("_t")
    field = {"CompareResult": "winners", "AttachCategoryResult": "category"}.get(
        kind if isinstance(kind, str) else ""
    )
    aliases = {item.alias or name for name, item in model_type.model_fields.items()}
    if field is None or field not in aliases or "cantSolve" in aliases:
        return None
    target = _response_type(
        model_type, kind == "AttachCategoryResult" and data.get("cantSolve") is True
    )
    try:
        return cast(Model, target.model_validate(data))
    except ValidationError as error:
        if issubclass(target, LazyValidatedModel):
            return cast(Model, target._lazy_construct(data, error))
        raise
