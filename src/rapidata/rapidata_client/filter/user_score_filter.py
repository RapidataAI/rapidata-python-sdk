from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.user_score_user_filter_model import (
    UserScoreUserFilterModel,
)


class UserScoreFilter(Filter):

    def __init__(self, lower_bound: int = 0, upper_bound: int = 1):
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound

    def to_model(self):
        return UserScoreUserFilterModel(
            _t="UserScoreFilter",
            upperbound=self.upper_bound,
            lowerbound=self.lower_bound,
        )
