from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.custom_user_filter_model import CustomUserFilterModel
from pydantic import BaseModel


class CustomFilter(RapidataFilter, BaseModel):
    """CustomFilter Class

    Can be used to filter who to target based on custom filters.

    Ought to be used with contact to Rapidata.

    Warning: If identifier does not exist, order will not get any responses.

    Args:
        identifier (str): Identifier of the custom filter.
        values (list[str]): List of values to filter by.
    """

    identifier: str
    values: list[str]

    def _to_model(self):
        return CustomUserFilterModel(
            _t="CustomFilter",
            identifier=self.identifier,
            values=self.values,
        )
