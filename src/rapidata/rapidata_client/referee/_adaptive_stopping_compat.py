from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Mapping


def normalise_adaptive_stopping_config(data: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve adaptive referee defaults and convert legacy binary ranges on reads."""
    resolved = {
        "maxVotes": 100,
        "minConfidence": 0.9,
        "ambiguityThreshold": 0.64,
        "unsolvableThreshold": 0.5,
        "maxOutcomeCount": 1,
        **data,
    }
    if "ambiguityThreshold" not in data and "ambiguityRange" in data:
        legacy_range = data["ambiguityRange"]
        if (
            isinstance(legacy_range, bool)
            or not isinstance(legacy_range, (int, float))
            or not 0 < legacy_range < 1
        ):
            raise ValueError(
                "Legacy ambiguityRange must be between 0 and 1 (exclusive)."
            )
        resolved["ambiguityThreshold"] = 1 - legacy_range**2
    resolved.pop("ambiguityRange", None)
    return resolved
