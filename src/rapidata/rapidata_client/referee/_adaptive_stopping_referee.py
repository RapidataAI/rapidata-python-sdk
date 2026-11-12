from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rapidata.rapidata_client.referee._base_referee import Referee

if TYPE_CHECKING:
    from rapidata.api_client.models.i_referee import IReferee


class AdaptiveStoppingReferee(Referee):
    """Wire form of ``AdaptiveStopping``; validation lives on the public class."""

    def __init__(
        self,
        max_votes: int | None,
        min_confidence: float | None,
        ambiguity_threshold: float | None,
    ):
        super().__init__()
        self.max_votes = max_votes
        self.min_confidence = min_confidence
        self.ambiguity_threshold = ambiguity_threshold

    def _set_fields(self) -> dict[str, Any]:
        fields: dict[str, int | float | None] = {
            "maxVotes": self.max_votes,
            "minConfidence": self.min_confidence,
            "ambiguityThreshold": self.ambiguity_threshold,
        }
        return {key: value for key, value in fields.items() if value is not None}

    def _to_dict(self):
        return {"_t": "AdaptiveStoppingRefereeConfig", **self._set_fields()}

    def _to_model(self) -> IReferee:
        from rapidata.api_client.models.i_referee_adaptive_stopping_referee import (
            IRefereeAdaptiveStoppingReferee,
        )
        from rapidata.api_client.models.i_referee import IReferee

        return IReferee(
            actual_instance=IRefereeAdaptiveStoppingReferee(
                _t="AdaptiveStoppingReferee", **self._set_fields()
            )
        )
