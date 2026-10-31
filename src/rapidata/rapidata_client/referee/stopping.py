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
    """Stop collecting votes on a compare pair as soon as its outcome is settled.

    Each vote is weighted by the voter's quality score at the time it was cast.
    After every vote, the pair stops once it is confident that one side wins
    (verdict ``"A"`` or ``"B"``), or that the pair is too close to call
    (verdict ``"ambiguous"``). A pair that reaches ``max_responses`` first ends
    as ``"undecided"``. Clear pairs stop after as few as 7 votes; on average a
    pair needs about 25 (measured on past compare jobs), and the hardest pairs
    (split around 35/65) about 31.

    The defaults are calibrated. Change them only if you know why.

    Args:
        min_confidence (float, optional): The lower bound on the probability that a
            verdict is correct, between 0 and 1. Defaults to 0.9.
        ambiguity_range (float, optional): The width of the ambiguous band centred on
            an even split, between 0 and 1. Defaults to 0.6, the band 20/80 to 80/20.
            Pairs whose split lies in the band may stop as ambiguous. Lowering it
            narrows the band, so closer pairs resolve to a winner, at the cost of more
            votes: 0.5 (25/75 to 75/25) needs about a third more votes on average, 0.3
            gives 35/65 to 65/35. A winner still beats ambiguous, so a 70/30 pair can
            return ``"A"`` or ``"B"`` at any range.
        max_responses (int, optional): A safety cap on votes per pair. Defaults to 100,
            which the default settings never reach.
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
