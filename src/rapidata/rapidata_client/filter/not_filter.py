from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.not_user_filter_model import NotUserFilterModel
from rapidata.api_client.models.and_user_filter_model_filters_inner import (
    AndUserFilterModelFiltersInner,
)
from pydantic import BaseModel, ConfigDict


class NotFilter(RapidataFilter, BaseModel):
    """A filter that negates another filter's condition.
    This class implements a logical NOT operation on a given filter, inverting its results.

    Args:
        filter (RapidataFilter): The filter whose condition should be negated.

    Example:
        ```python
        from rapidata import NotFilter, LanguageFilter

        NotFilter(LanguageFilter(["en"]))
        ```

        This will limit the order to be shown to only people who have their phone set to a language other than English.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    filter: RapidataFilter

    def __init__(self, filter: RapidataFilter):
        super().__init__(filter=filter)

    def _to_model(self):
        return NotUserFilterModel(
            _t="NotFilter",
            filter=AndUserFilterModelFiltersInner(self.filter._to_model()),
        )
