from __future__ import annotations

from rapidata.rapidata_client.referee._base_referee import Referee
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.i_referee import IReferee


class AdaptiveStoppingReferee(Referee):
    """A compare referee that stops each pair once its verdict is statistically settled.

    Configured through :class:`~rapidata.AdaptiveStopping`; see there for the parameters.
    """

    def __init__(self, min_confidence: float, ambiguity: float, max_responses: int):
        self.min_confidence = min_confidence
        self.ambiguity = ambiguity
        self.max_responses = max_responses

    def _to_dict(self):
        return {
            "_t": "AdaptiveStoppingRefereeConfig",
            "maxVotes": self.max_responses,
            "minConfidence": self.min_confidence,
            "ambiguity": self.ambiguity,
        }

    def _to_model(self) -> IReferee:
        from rapidata.api_client.models.i_referee_adaptive_stopping_referee import (
            IRefereeAdaptiveStoppingReferee,
        )
        from rapidata.api_client.models.i_referee import IReferee

        return IReferee(
            actual_instance=IRefereeAdaptiveStoppingReferee(
                _t="AdaptiveStoppingReferee",
                maxVotes=self.max_responses,
                minConfidence=self.min_confidence,
                ambiguity=self.ambiguity,
            )
        )

    def __str__(self) -> str:
        return (
            f"AdaptiveStoppingReferee(min_confidence={self.min_confidence}, "
            f"ambiguity={self.ambiguity}, max_responses={self.max_responses})"
        )

    def __repr__(self) -> str:
        return self.__str__()
