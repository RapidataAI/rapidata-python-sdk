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

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from rapidata.rapidata_client.config import logger, tracer


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

        # --- observability: log error + fail the trace ---
        error_fields = list(field_errors.keys())
        logger.warning(
            "Validation failed for %s – mismatched fields: %s",
            cls.__name__,
            error_fields,
            exc_info=error,
        )

        tracer.fail_current_span(
            f"Validation failed for {cls.__name__}: {error_fields}"
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
        # Use getattr (MRO-aware) rather than type(self).__dict__.get():
        # in Pydantic v2, fields are exposed via the `model_fields`
        # class-property and are NOT present in the class's own __dict__,
        # so a __dict__ lookup always misses and the guard never fires.
        model_fields = getattr(type(self), "model_fields", None)
        if model_fields is not None and name in model_fields:
            # model_construct() bypasses __init__, so `_field_validation_errors`
            # may not be set on every instance. Treat missing as "no errors".
            errors: Optional[Dict[str, dict]]
            try:
                errors = object.__getattribute__(
                    self, "_field_validation_errors"
                )
            except AttributeError:
                errors = None
            if errors and name in errors:
                err = errors[name]
                raise TypeError(
                    f"Field '{name}' on {type(self).__name__} has an unexpected "
                    f"type from the backend: {err.get('msg', err)}"
                )
        return super().__getattribute__(name)
