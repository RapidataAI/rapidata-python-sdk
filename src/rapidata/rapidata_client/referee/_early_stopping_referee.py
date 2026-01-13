from __future__ import annotations

from rapidata.rapidata_client.referee._base_referee import Referee
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.i_referee_model import IRefereeModel


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
        max_responses (int, optional): The maximum number of votes allowed
            before stopping. Defaults to 100.

    Attributes:
        threshold (float): The confidence threshold for early stopping.
        max_responses (int): The maximum number of votes allowed before stopping.
    """

    def __init__(self, threshold: float = 0.999, max_responses: int = 100):
        if threshold <= 0 or threshold >= 1:
            raise ValueError("The threshold must be between 0 and 1.")
        if max_responses < 1:
            raise ValueError("The number of responses must be greater than 0.")

        self.threshold = threshold
        self.max_responses = max_responses

    def _to_dict(self):
        return {
            "_t": "ProbabilisticAttachCategoryRefereeConfig",
            "threshold": self.threshold,
            "maxVotes": self.max_responses,
        }

    def _to_model(self) -> IRefereeModel:
        from rapidata.api_client.models.i_referee_model_early_stopping_referee_model import (
            IRefereeModelEarlyStoppingRefereeModel,
        )
        from rapidata.api_client.models.i_referee_model import IRefereeModel

        return IRefereeModel(
            actual_instance=IRefereeModelEarlyStoppingRefereeModel(
                _t="EarlyStoppingReferee",
                threshold=self.threshold,
                maxVotes=self.max_responses,
            )
        )

    def __str__(self) -> str:
        return f"EarlyStoppingReferee(threshold={self.threshold}, max_responses={self.max_responses})"

    def __repr__(self) -> str:
        return self.__str__()
