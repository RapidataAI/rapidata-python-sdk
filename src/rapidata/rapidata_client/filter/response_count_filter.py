from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.response_count_user_filter_model import (
    ResponseCountUserFilterModel,
)

class ResponseCountFilter(RapidataFilter):
    """ResponseCountFilter Class
    Can be used to filter users based on the number of responses they have given on validation tasks with the specified dimension.

        response_count (int): The number of user responses to filter by.
        dimension (str): The dimension to apply the filter on (e.g. "default", "electrical", etc.).
        operator (str): The comparison operator to use. Must be one of:
            - "Equal"
            - "NotEqual"
            - "LessThan"
            - "LessThanOrEqual"
            - "GreaterThan"
            - "GreaterThanOrEqual"

    Raises:
        ValueError: If `response_count` is not an integer.
        ValueError: If `dimension` is not a string.
        ValueError: If `operator` is not a string or not one of the allowed values.

    Example:
        ```python
        from rapidata import ResponseCountFilter

        filter = ResponseCountFilter(response_count=10, dimension="electrical", operator="GreaterThan")
        ```
        This will filter users who have a response count greater than 10 for the "electrical" dimension.
    """

    def __init__(self, response_count: int, dimension: str, operator: str):
        if operator not in ["Equal", "NotEqual", "LessThan", "LessThanOrEqual", "GreaterThan", "GreaterThanOrEqual"]:
            raise ValueError("Operator must be one of Equal, NotEqual, LessThan, LessThanOrEqual, GreaterThan, GreaterThanOrEqual")

        self.response_count = response_count
        self.dimension = dimension
        self.operator = operator

    def _to_model(self):
        return ResponseCountUserFilterModel(
            _t="ResponseCountFilter", responseCount=self.response_count, dimension=self.dimension, operator=self.operator
        )
