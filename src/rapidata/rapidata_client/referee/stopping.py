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
    pair needs about 25 (measured on past compare jobs), and the hardest pairs (split around 35/65) about 31.

    The defaults are calibrated. Change them only if you know why.

    Args:
        min_confidence (float, optional): The lower bound on the probability that a
            verdict is correct, between 0 and 1. Defaults to 0.9.
        ambiguity (float, optional): How even a pair has to be to count as
            ambiguous, between 0 and 0.5. A pair whose true share of votes for B is
            ``q`` is ambiguous when ``2q(1-q) >= ambiguity``; the default 0.32 makes
            every split between 20/80 and 80/20 ambiguous. Raising it narrows that
            band, so near-even pairs resolve to a winner, at the cost of more votes:
            0.375 (a 25/75 to 75/25 band) needs about a third more votes on average.
        max_responses (int, optional): A safety cap on votes per pair. Defaults to 100,
            which the default settings never reach.
    """

    min_confidence: float = 0.9
    ambiguity: float = 0.32
    max_responses: int = 100

    def __post_init__(self) -> None:
        if not _is_number(self.min_confidence) or not 0 < self.min_confidence < 1:
            raise ValueError("min_confidence must be between 0 and 1 (exclusive).")
        if not _is_number(self.ambiguity) or not 0 < self.ambiguity < 0.5:
            raise ValueError("ambiguity must be between 0 and 0.5 (exclusive).")
        if not _is_int(self.max_responses) or self.max_responses < 1:
            raise ValueError("max_responses must be a positive integer.")

    def _to_referee(self) -> Referee:
        from rapidata.rapidata_client.referee._adaptive_stopping_referee import (
            AdaptiveStoppingReferee,
        )

        return AdaptiveStoppingReferee(
            min_confidence=float(self.min_confidence),
            ambiguity=float(self.ambiguity),
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
