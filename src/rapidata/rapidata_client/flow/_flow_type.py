from __future__ import annotations

from typing import Literal

FlowType = Literal["ranking", "simple"]

_API_FLOW_TYPES: dict[str, FlowType] = {
    "Ranking": "ranking",
    "RankingFlow": "ranking",
    "Simple": "simple",
    "SimpleFlow": "simple",
}


def flow_type_from_api(value: str) -> FlowType:
    """Map the API's flow type enum value or `_t` discriminator to the SDK flow type."""
    try:
        return _API_FLOW_TYPES[value]
    except KeyError:
        raise ValueError(
            f"Unknown flow type '{value}'. Update the rapidata package to the latest version."
        ) from None
