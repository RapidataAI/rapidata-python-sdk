from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.and_user_filter_model import AndUserFilterModel
from rapidata.api_client.models.and_user_filter_model_filters_inner import AndUserFilterModelFiltersInner


class AndFilter(RapidataFilter):
    """A filter that combines multiple filters with a logical AND operation.
    This class implements a logical AND operation on a list of filters, where the condition is met if all of the filters' conditions are met.

    Args:
        filters (list[RapidataFilter]): A list of filters to be combined with AND.
        
    Example:
        ```python
        from rapidata import AndFilter, LanguageFilter, CountryFilter

        AndFilter([LanguageFilter(["en"]), CountryFilter(["US"])]) 
        ```

        This will match users who have their phone set to English AND are located in the United States.
    """
    def __init__(self, filters: list[RapidataFilter]):
        if not all(isinstance(filter, RapidataFilter) for filter in filters):
            raise ValueError("Filters must be a RapidataFilter object")
        
        self.filters = filters

    def _to_model(self):
        return AndUserFilterModel(_t="AndFilter", filters=[AndUserFilterModelFiltersInner(filter._to_model()) for filter in self.filters])
