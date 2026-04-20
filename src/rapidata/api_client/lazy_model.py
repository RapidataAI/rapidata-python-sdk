"""Lazy-validated Pydantic base model for generated API models.

Replaces ``BaseModel`` as the parent of every generated model so that
construction never raises on a type mismatch.  Instead, per-field
validation errors are logged, recorded on the current OpenTelemetry
span, and stored on the instance.  A ``TypeError`` is raised only when
the caller actually *accesses* a field whose value failed validation.

This means backend schema changes that affect unused fields no longer
break SDK callers, while type-safety is preserved for fields that are
read.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Union

from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, ValidationError

logger = logging.getLogger("rapidata")


class LazyValidatedModel(BaseModel):
    """BaseModel subclass with deferred per-field validation."""

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    # ------------------------------------------------------------------
    # Normal construction path – mark the instance as error-free
    # ------------------------------------------------------------------
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # Fast-path flag so __getattribute__ can skip the dict lookup
        # for the vast majority of instances that validated cleanly.
        object.__setattr__(self, "_field_validation_errors", {})

    # ------------------------------------------------------------------
    # Fallback construction – called when model_validate raises
    # ------------------------------------------------------------------
    @classmethod
    def _lazy_construct(
        cls,
        data: Dict[str, Any],
        error: ValidationError,
    ) -> "LazyValidatedModel":
        """Build the model via ``model_construct`` and store per-field errors."""

        # --- alias → python field name mapping ---
        alias_to_field: Dict[str, str] = {}
        for field_name, field_info in cls.model_fields.items():
            alias = field_info.alias or field_name
            alias_to_field[alias] = field_name
            alias_to_field[field_name] = field_name

        # --- build kwargs with python names for model_construct ---
        construct_kwargs: Dict[str, Any] = {}
        for key, value in data.items():
            python_name = alias_to_field.get(key, key)
            construct_kwargs[python_name] = value

        # --- extract per-field errors keyed by python name ---
        field_errors: Dict[str, Any] = {}
        for err in error.errors():
            loc = err.get("loc", ())
            if loc:
                alias_key = str(loc[0])
                python_name = alias_to_field.get(alias_key, alias_key)
                field_errors[python_name] = err

        # --- observability: log + trace event ---
        error_fields = list(field_errors.keys())
        logger.warning(
            "Lazy validation fallback for %s – mismatched fields: %s",
            cls.__name__,
            error_fields,
        )

        span = trace.get_current_span()
        if span.is_recording():
            span.add_event(
                "lazy_validation_fallback",
                {
                    "model": cls.__name__,
                    "mismatched_fields": str(error_fields),
                    "error_count": len(field_errors),
                },
            )

        # --- construct without validation ---
        instance = cls.model_construct(**construct_kwargs)
        object.__setattr__(instance, "_field_validation_errors", field_errors)
        return instance

    # ------------------------------------------------------------------
    # Access-time guard – raise only when a bad field is actually read
    # ------------------------------------------------------------------
    def __getattribute__(self, name: str) -> Any:
        # Only intercept known model fields; everything else takes the
        # fast super() path (Pydantic internals, dunder attrs, methods).
        model_fields = type(self).__dict__.get("model_fields")
        if model_fields is not None and name in model_fields:
            errors: Dict[str, dict] = object.__getattribute__(
                self, "_field_validation_errors"
            )
            if errors and name in errors:
                err = errors[name]
                raise TypeError(
                    f"Field '{name}' on {type(self).__name__} has an unexpected "
                    f"type from the backend: {err.get('msg', err)}"
                )
        return super().__getattribute__(name)
