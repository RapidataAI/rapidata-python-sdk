from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rapidata.rapidata_client.referee._adaptive_stopping_compat import (
    normalise_adaptive_stopping_config,
)

if TYPE_CHECKING:
    from typing import Any, Mapping
    from rapidata.rapidata_client.referee._base_referee import Referee


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class AdaptiveStopping:
    """Stop collecting responses when the configured decision rule is met.

    Responses are weighted by the labeler's user score at response time.
    Confidence for weighted evidence is heuristic, not a coverage guarantee.

    Args:
        min_confidence (float, optional): Model confidence threshold in (0, 1).
            Defaults to 0.9.
        ambiguity_threshold (float, optional): Normalized disagreement threshold
            in (0, 1). Defaults to 0.64.
        max_responses (int, optional): Maximum responses per datapoint.
            Defaults to 100.
        max_outcome_count (int, optional): Maximum size of a leading set.
            Defaults to 1; must be smaller than the substantive outcome count.
        unsolvable_threshold (float, optional): Threshold for explicit can't solve
            in (0, 1). Defaults to 0.5; enabling the response is separate.
    """

    min_confidence: float = 0.9
    ambiguity_threshold: float = 0.64
    max_responses: int = 100
    max_outcome_count: int = 1
    unsolvable_threshold: float = 0.5

    def __post_init__(self) -> None:
        if not _is_number(self.min_confidence) or not 0 < self.min_confidence < 1:
            raise ValueError("min_confidence must be between 0 and 1 (exclusive).")
        if (
            not _is_number(self.ambiguity_threshold)
            or not 0 < self.ambiguity_threshold < 1
        ):
            raise ValueError("ambiguity_threshold must be between 0 and 1 (exclusive).")
        if not _is_int(self.max_responses) or self.max_responses < 1:
            raise ValueError("max_responses must be a positive integer.")
        if not _is_int(self.max_outcome_count) or self.max_outcome_count < 1:
            raise ValueError("max_outcome_count must be a positive integer.")
        if (
            not _is_number(self.unsolvable_threshold)
            or not 0 < self.unsolvable_threshold < 1
        ):
            raise ValueError(
                "unsolvable_threshold must be between 0 and 1 (exclusive)."
            )

    @classmethod
    def _from_dict(cls, data: Mapping[str, Any]) -> AdaptiveStopping:
        data = normalise_adaptive_stopping_config(data)
        return cls(
            min_confidence=data["minConfidence"],
            ambiguity_threshold=data["ambiguityThreshold"],
            max_responses=data["maxVotes"],
            max_outcome_count=data["maxOutcomeCount"],
            unsolvable_threshold=data["unsolvableThreshold"],
        )

    def _to_referee(self) -> Referee:
        from rapidata.rapidata_client.referee._adaptive_stopping_referee import (
            AdaptiveStoppingReferee,
        )

        return AdaptiveStoppingReferee(
            min_confidence=float(self.min_confidence),
            ambiguity_threshold=float(self.ambiguity_threshold),
            max_responses=self.max_responses,
            max_outcome_count=self.max_outcome_count,
            unsolvable_threshold=float(self.unsolvable_threshold),
        )

    def _validate_outcome_count(self, outcome_count: int) -> None:
        if self.max_outcome_count >= outcome_count:
            raise ValueError(
                "max_outcome_count must be smaller than the number of substantive outcomes."
            )


@dataclass(frozen=True)
class QuorumStopping:
    """Stop collecting responses on a datapoint once enough of them agree.

    A datapoint stops when ``threshold`` responses pick the same answer, when that
    can no longer happen within ``max_responses``, or at ``max_responses``.

    Args:
        threshold (int): The number of matching responses that ends the datapoint.
        max_responses (int): The most responses collected per datapoint.
    """

    threshold: int
    max_responses: int

    def __post_init__(self) -> None:
        if not _is_int(self.threshold) or self.threshold < 1:
            raise ValueError("threshold must be a positive integer.")
        if not _is_int(self.max_responses) or self.max_responses < 1:
            raise ValueError("max_responses must be a positive integer.")
        if self.threshold > self.max_responses:
            raise ValueError("threshold cannot be greater than max_responses.")

    def _to_referee(self) -> Referee:
        from rapidata.rapidata_client.referee._quorum_referee import QuorumReferee

        return QuorumReferee(threshold=self.threshold, max_votes=self.max_responses)
