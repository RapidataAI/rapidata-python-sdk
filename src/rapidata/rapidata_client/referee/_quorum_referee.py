from __future__ import annotations

from rapidata.rapidata_client.referee._base_referee import Referee
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.i_referee_model import IRefereeModel


class QuorumReferee(Referee):
    """A referee that completes a task when a specified number of responses agree.

    This referee implements a quorum-based approach where a task is completed when:
    1. A minimum number of responses (threshold) agree on the same answer, OR
    2. Quorum becomes mathematically impossible to reach, OR
    3. The maximum number of votes is reached

    For example, with threshold=7 and max_votes=10:
    - Task completes when 7 responses agree (quorum reached)
    - Task completes when both options have 4+ responses (quorum impossible: 4+4=8 > 10-7)
    - Task completes after 10 total votes if neither condition is met

    Args:
        threshold (int, optional): The number of matching responses required
            to reach quorum. Defaults to 3.
        max_votes (int, optional): The maximum number of votes allowed
            before stopping. Defaults to 5.

    Attributes:
        threshold (int): The number of matching responses required to reach quorum.
        max_votes (int): The maximum number of votes allowed before stopping.
    """

    def __init__(self, threshold: int = 3, max_votes: int = 5):
        if threshold < 1:
            raise ValueError("The threshold must be greater than 0.")
        if max_votes < 1:
            raise ValueError("The number of max_votes must be greater than 0.")
        if threshold > max_votes:
            raise ValueError("The threshold cannot be greater than max_votes.")

        super().__init__()
        if not isinstance(threshold, int) or not isinstance(max_votes, int):
            raise ValueError(
                "The the quorum threshold and responses_per_datapoint must be integers."
            )
        self.threshold = threshold
        self.max_votes = max_votes

    def _to_dict(self):
        return {
            "_t": "QuorumRefereeConfig",
            "maxVotes": self.max_votes,
            "threshold": self.threshold,
        }

    def _to_model(self) -> IRefereeModel:
        from rapidata.api_client.models.i_referee_model_quorum_referee_model import (
            IRefereeModelQuorumRefereeModel,
        )
        from rapidata.api_client.models.i_referee_model import IRefereeModel

        return IRefereeModel(
            actual_instance=IRefereeModelQuorumRefereeModel(
                _t="QuorumReferee",
                maxVotes=self.max_votes,
                threshold=self.threshold,
            )
        )

    def __str__(self) -> str:
        return f"QuorumReferee(threshold={self.threshold}, max_votes={self.max_votes})"

    def __repr__(self) -> str:
        return self.__str__()
