from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.rapidata_client.referee._quorum_referee import QuorumReferee


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class QuorumStopping:
    """Stops collecting responses on a datapoint once enough of them agree.

    A datapoint stops when ``threshold`` responses pick the same answer, when that
    can no longer happen within ``max_responses``, or at ``max_responses``.

    Pass it as ``responses_per_datapoint`` on classification and compare job
    definitions, or assign it to ``RapidataJobDefinition.responses_per_datapoint``.
    Other job types raise ``ValueError``.

    Args:
        threshold (int): The number of matching responses that ends the datapoint.
        max_responses (int): The most responses collected per datapoint.

    Attributes:
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

    def _to_referee(self) -> QuorumReferee:
        from rapidata.rapidata_client.referee._quorum_referee import QuorumReferee

        return QuorumReferee(threshold=self.threshold, max_votes=self.max_responses)
