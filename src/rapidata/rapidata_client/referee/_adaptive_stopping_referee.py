from __future__ import annotations

from rapidata.rapidata_client.referee._base_referee import Referee
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.i_referee import IReferee


class AdaptiveStoppingReferee(Referee):
    """A score-weighted categorical referee configured through AdaptiveStopping."""

    def __init__(
        self,
        min_confidence: float,
        ambiguity_threshold: float,
        max_responses: int,
        max_outcome_count: int,
        unsolvable_threshold: float,
    ):
        self.min_confidence = min_confidence
        self.ambiguity_threshold = ambiguity_threshold
        self.max_responses = max_responses
        self.max_outcome_count = max_outcome_count
        self.unsolvable_threshold = unsolvable_threshold

    def _to_dict(self):
        return {
            "_t": "AdaptiveStoppingRefereeConfig",
            "maxVotes": self.max_responses,
            "minConfidence": self.min_confidence,
            "ambiguityThreshold": self.ambiguity_threshold,
            "unsolvableThreshold": self.unsolvable_threshold,
            "maxOutcomeCount": self.max_outcome_count,
        }

    def _to_model(self) -> IReferee:
        from rapidata.api_client.models.i_referee import IReferee

        data = {**self._to_dict(), "_t": "AdaptiveStoppingReferee"}
        return IReferee.from_dict(data)

    def __str__(self) -> str:
        return (
            f"AdaptiveStoppingReferee(min_confidence={self.min_confidence}, "
            f"ambiguity_threshold={self.ambiguity_threshold}, "
            f"max_responses={self.max_responses}, max_outcome_count={self.max_outcome_count}, "
            f"unsolvable_threshold={self.unsolvable_threshold})"
        )

    def __repr__(self) -> str:
        return self.__str__()
