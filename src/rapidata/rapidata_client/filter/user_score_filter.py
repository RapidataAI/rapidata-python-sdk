from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.user_score_user_filter_model import (
    UserScoreUserFilterModel,
)


class UserScoreFilter(RapidataFilter):
    """UserScoreFilter Class
    
    Can be used to filter who to target based on their user score.
    
    example: UserScoreFilter(0.5, 0.9) -> will only show the order to users that have a UserScore of >=0.5 and <=0.9

    Args:
        lower_bound (float): The lower bound of the user score.
        upper_bound (float): The upper bound of the user score.
    """
    def __init__(self, lower_bound: float = 0.0, upper_bound: float = 1.0):
        if lower_bound < 0 or lower_bound > 1:
            raise ValueError("The lower bound must be between 0 and 1.")
        if upper_bound < 0 or upper_bound > 1:
            raise ValueError("The upper bound must be between 0 and 1.")
        if lower_bound >= upper_bound:
            raise ValueError("The lower bound must be less than the upper bound.")
        
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound

    def _to_model(self):
        return UserScoreUserFilterModel(
            _t="UserScoreFilter",
            upperbound=self.upper_bound,
            lowerbound=self.lower_bound,
        )
