from __future__ import annotations

import os
import types as _types
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union, get_args, get_origin

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

_ENV_PREFIX = "RAPIDATA_"
_SIMPLE_SCALARS = frozenset({str, int, float, Path})


def apply_env_overrides(model_fields: dict[str, FieldInfo], data: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to model data.

    For each model field not already in ``data``, checks for an environment
    variable named ``RAPIDATA_<fieldName>``.  If found the value is parsed
    and injected into ``data`` so that Pydantic can validate it normally.

    Bool fields accept ``"1"`` / ``"true"`` / ``"yes"`` (case-insensitive).
    Scalar types (str, int, float, Path) are passed as strings and coerced
    by Pydantic in lax mode.  Complex types (BaseModel sub-classes, etc.)
    are silently skipped.
    """
    for field_name, field_info in model_fields.items():
        if field_name in data:
            continue
        env_value = os.environ.get(f"{_ENV_PREFIX}{field_name}")
        if env_value is None:
            continue

        is_optional = _is_optional(field_info.annotation)
        base_type = _unwrap_optional(field_info.annotation)

        # Treat empty strings as "not set" for optional fields
        if is_optional and env_value == "":
            continue

        if base_type is bool:
            data[field_name] = env_value.lower() in ("1", "true", "yes")
        elif base_type is Path:
            data[field_name] = Path(env_value).expanduser()
        elif base_type in _SIMPLE_SCALARS:
            data[field_name] = env_value
    return data


def _is_optional(annotation: Any) -> bool:
    """Return ``True`` if the annotation is ``Optional[T]`` / ``T | None``."""
    origin = get_origin(annotation)
    if origin is Union or origin is _types.UnionType:
        return type(None) in get_args(annotation)
    return False


def _unwrap_optional(annotation: Any) -> Any:
    """Unwrap ``Optional[T]`` / ``T | None`` to ``T``.

    Returns the annotation unchanged when it is not an Optional wrapper.
    """
    origin = get_origin(annotation)
    if origin is Union or origin is _types.UnionType:
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation
