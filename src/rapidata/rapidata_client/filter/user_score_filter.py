from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.user_score_user_filter_model import (
    UserScoreUserFilterModel,
)


class UserScoreFilter(Filter):

    def __init__(self, upper_bound: int, lower_bound: int):
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound

    def to_model(self) -> Any:
        return UserScoreUserFilterModel(
            _t="UserScoreFilter",
            upperbound=self.upper_bound,
            lowerbound=self.lower_bound,
        )
