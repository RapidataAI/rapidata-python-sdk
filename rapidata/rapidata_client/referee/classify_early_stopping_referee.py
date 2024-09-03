from typing import Any
from rapidata.rapidata_client.referee.base_referee import Referee
from rapidata.api_client.models.early_stopping_referee_model import EarlyStoppingRefereeModel


class ClassifyEarlyStoppingReferee(Referee):
    """
    The referee defines when a task is considered complete.
    The EarlyStoppingReferee stops the task when the confidence in the winning category is above a threshold.
    The threshold behaves logarithmically, i.e. if 0.99 stops too early, try 0.999 or 0.9999.
    """

    def __init__(self, threshold: float = 0.999, max_vote_count: int = 100):
        self.threshold = threshold
        self.max_vote_count = max_vote_count

    def to_dict(self):
        return {
            "_t": "ProbabilisticAttachCategoryRefereeConfig",
            "threshold": self.threshold,
            "maxVotes": self.max_vote_count,
        }

    def to_model(self) -> Any:
        return EarlyStoppingRefereeModel(
            _t="EarlyStoppingReferee",
            threshold=self.threshold,
            max_votes=self.max_vote_count,
        )
