from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.custom_user_filter_model import CustomUserFilterModel


class CustomFilter(RapidataFilter):
    """CustomFilter Class

    Can be used to filter who to target based on custom filters.

    Ought to be used with contact to Rapidata. 
    
    Warning: If identifier does not exist, order will not get any responses.
    
    Args:
        identifier (str): Identifier of the custom filter.
        values (list[str]): List of values to filter by.
    """

    def __init__(self, identifier: str, values: list[str]):
        self.identifier = identifier
        self.values = values

    def _to_model(self):
        return CustomUserFilterModel(
            _t="CustomFilter",
            identifier=self.identifier,
            values=self.values,
        )
