from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.response_count_user_filter_model import (
    ResponseCountUserFilterModel,
)
from rapidata.api_client.models.comparison_operator import ComparisonOperator
from pydantic import BaseModel, ConfigDict


class ResponseCountFilter(RapidataFilter, BaseModel):
    """ResponseCountFilter Class
    Can be used to filter users based on the number of responses they have given on validation tasks with the specified dimension.

        response_count (int): The number of user responses to filter by.
        dimension (str): The dimension to apply the filter on (e.g. "default", "electrical", etc.).
        operator (str): The comparison operator to use. Must be one of:
            - ComparisonOperator.EQUAL
            - ComparisonOperator.NOTEQUAL
            - ComparisonOperator.LESSTHAN
            - ComparisonOperator.LESSTHANOREQUAL
            - ComparisonOperator.GREATERTHAN
            - ComparisonOperator.GREATERTHANOREQUAL

    Raises:
        ValueError: If `response_count` is not an integer.
        ValueError: If `dimension` is not a string.
        ValueError: If `operator` is not a string or not one of the allowed values.

    Example:
        ```python
        from rapidata import ResponseCountFilter

        filter = ResponseCountFilter(response_count=10, dimension="electrical", operator=ComparisonOperator.GREATERTHAN)
        ```
        This will filter users who have a response count greater than 10 for the "electrical" dimension.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    response_count: int
    dimension: str
    operator: ComparisonOperator

    def __init__(
        self, response_count: int, dimension: str, operator: ComparisonOperator
    ):
        super().__init__(
            response_count=response_count, dimension=dimension, operator=operator
        )

    def _to_model(self):
        return ResponseCountUserFilterModel(
            _t="ResponseCountFilter",
            responseCount=self.response_count,
            dimension=self.dimension,
            operator=self.operator,
        )
