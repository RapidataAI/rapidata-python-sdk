from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
        ambiguity_range (float, optional): Legacy binary ambiguity band width
            centered on an even split, in (0, 1). Defaults to 0.6.
        max_responses (int, optional): Maximum responses per datapoint.
            Defaults to 100.
    """

    min_confidence: float = 0.9
    ambiguity_range: float = 0.6
    max_responses: int = 100

    def __post_init__(self) -> None:
        if not _is_number(self.min_confidence) or not 0 < self.min_confidence < 1:
            raise ValueError("min_confidence must be between 0 and 1 (exclusive).")
        if not _is_number(self.ambiguity_range) or not 0 < self.ambiguity_range < 1:
            raise ValueError("ambiguity_range must be between 0 and 1 (exclusive).")
        if not _is_int(self.max_responses) or self.max_responses < 1:
            raise ValueError("max_responses must be a positive integer.")

    def _to_referee(self) -> Referee:
        from rapidata.rapidata_client.referee._adaptive_stopping_referee import (
            AdaptiveStoppingReferee,
        )

        return AdaptiveStoppingReferee(
            min_confidence=float(self.min_confidence),
            ambiguity_range=float(self.ambiguity_range),
            max_responses=self.max_responses,
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
