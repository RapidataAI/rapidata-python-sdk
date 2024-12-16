from typing import Any
from rapidata.rapidata_client.referee._base_referee import Referee
from rapidata.api_client.models.early_stopping_referee_model import (
    EarlyStoppingRefereeModel,
)


class EarlyStoppingReferee(Referee):
    """A referee that stops the task when confidence in the winning category exceeds a threshold.

    This referee implements an early stopping mechanism for classification & compare tasks.
    It terminates the task when the confidence in the leading category surpasses
    a specified threshold or when the maximum number of votes is reached.

    The threshold behaves logarithmically, meaning small increments (e.g., from 0.99
    to 0.999) can significantly impact the stopping criteria.

    This referee is supported for the classification and compare tasks (in compare, 
    the two options are treated as the categories).

    Args:
        threshold (float, optional): The confidence threshold for early stopping.
            Defaults to 0.999.
        max_vote_count (int, optional): The maximum number of votes allowed
            before stopping. Defaults to 100.

    Attributes:
        threshold (float): The confidence threshold for early stopping.
        max_vote_count (int): The maximum number of votes allowed before stopping.
    """

    def __init__(self, threshold: float = 0.999, max_vote_count: int = 100):
        if threshold <= 0 or threshold >= 1:
            raise ValueError("The threshold must be between 0 and 1.")
        if max_vote_count < 1:
            raise ValueError("The number of responses must be greater than 0.")
        
        self.threshold = threshold
        self.max_vote_count = max_vote_count

    def _to_dict(self):
        return {
            "_t": "ProbabilisticAttachCategoryRefereeConfig",
            "threshold": self.threshold,
            "maxVotes": self.max_vote_count,
        }

    def _to_model(self) -> Any:
        return EarlyStoppingRefereeModel(
            _t="EarlyStoppingReferee",
            threshold=self.threshold,
            maxVotes=self.max_vote_count,
        )
