from pydantic_core.core_schema import FieldValidationInfo
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.user_score_user_filter_model import (
    UserScoreUserFilterModel,
)
from pydantic import BaseModel, field_validator, model_validator


class UserScoreFilter(RapidataFilter, BaseModel):
    """UserScoreFilter Class

    Can be used to filter who to target based on their user score.

    Args:
        lower_bound (float): The lower bound of the user score.
        upper_bound (float): The upper bound of the user score.
        dimension (str): The dimension of the userScore to be considerd for the filter.

    Example:
        ```python
        UserScoreFilter(0.5, 0.9)
        ```
        This will only show the order to users that have a UserScore of >=0.5 and <=0.9
    """

    lower_bound: float
    upper_bound: float
    dimension: str | None = None

    def __init__(
        self,
        lower_bound: float = 0.0,
        upper_bound: float = 1.0,
        dimension: str | None = None,
    ):
        super().__init__(
            lower_bound=lower_bound, upper_bound=upper_bound, dimension=dimension
        )

    @field_validator("lower_bound", "upper_bound")
    @classmethod
    def validate_bounds(cls, v: float, info: FieldValidationInfo) -> float:
        if v < 0 or v > 1:
            raise ValueError(f"{info.field_name} must be between 0 and 1")
        return v

    @model_validator(mode="after")
    def validate_bounds_relationship(self) -> "UserScoreFilter":
        if self.lower_bound >= self.upper_bound:
            raise ValueError("lower_bound must be less than upper_bound")
        return self

    def _to_model(self):
        return UserScoreUserFilterModel(
            _t="UserScoreFilter",
            upperbound=self.upper_bound,
            lowerbound=self.lower_bound,
            dimension=self.dimension,
        )
