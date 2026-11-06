from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, TypeVar, cast, get_args

from pydantic import Field, model_serializer

from rapidata.api_client.lazy_model import LazyValidatedModel
from rapidata.rapidata_client.referee._adaptive_stopping_compat import (
    normalise_adaptive_stopping_config,
)
from rapidata.rapidata_client.referee.stopping import AdaptiveStopping

RefereeModel = TypeVar("RefereeModel", bound=LazyValidatedModel)
_CONFIG_FIELDS = {
    "maxVotes",
    "minConfidence",
    "ambiguityThreshold",
    "unsolvableThreshold",
    "maxOutcomeCount",
}


class _AdaptiveWireModel(LazyValidatedModel):
    wire: dict[str, Any] = Field(exclude=True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.wire)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @model_serializer(mode="plain")
    def serialize(self) -> dict[str, Any]:
        return self.to_dict()


@lru_cache(maxsize=None)
def _adapter_type(model_type: type[RefereeModel]) -> type[RefereeModel]:
    return cast(
        type[RefereeModel],
        type(
            f"_Adaptive{model_type.__name__}",
            (_AdaptiveWireModel, model_type),
            {"__module__": __name__},
        ),
    )


def adapt_referee_model(
    model_type: type[RefereeModel], data: Any, discriminator: str
) -> RefereeModel | None:
    """Preserve canonical adaptive fields until the generated union supports them."""
    if not isinstance(data, dict) or data.get("_t") != discriminator:
        return None
    for variant in get_args(model_type.model_fields["actual_instance"].annotation):
        if isinstance(variant, type) and issubclass(variant, LazyValidatedModel):
            aliases = {
                field.alias or name for name, field in variant.model_fields.items()
            }
            if _CONFIG_FIELDS <= aliases:
                return None

    wire = normalise_adaptive_stopping_config(data)
    AdaptiveStopping._from_dict(wire)
    return cast(RefereeModel, _adapter_type(model_type)(wire=wire))
