from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.not_user_filter_model import NotUserFilterModel
from rapidata.api_client.models.and_user_filter_model_filters_inner import AndUserFilterModelFiltersInner


class NotFilter(RapidataFilter):
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
    def __init__(self, filter: RapidataFilter):
        if not isinstance(filter, RapidataFilter):
            raise ValueError("Filter must be a RapidataFilter object")
        
        self.filter = filter

    def _to_model(self):
        return NotUserFilterModel(_t="NotFilter", filter=AndUserFilterModelFiltersInner(self.filter._to_model()))
