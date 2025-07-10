from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.or_user_filter_model import OrUserFilterModel
from rapidata.api_client.models.and_user_filter_model_filters_inner import AndUserFilterModelFiltersInner


class OrFilter(RapidataFilter):
    """A filter that combines multiple filters with a logical OR operation.
    This class implements a logical OR operation on a list of filters, where the condition is met if any of the filters' conditions are met.

    Args:
        filters (list[RapidataFilter]): A list of filters to be combined with OR.
        
    Example:
        ```python
        from rapidata import OrFilter, LanguageFilter, CountryFilter

        OrFilter([LanguageFilter(["en"]), CountryFilter(["US"])]) 
        ```

        This will match users who either have their phone set to English OR are located in the United States.
    """
    def __init__(self, filters: list[RapidataFilter]):
        if not all(isinstance(filter, RapidataFilter) for filter in filters):
            raise ValueError("Filters must be a RapidataFilter object")
        
        self.filters = filters

    def _to_model(self):
        return OrUserFilterModel(_t="OrFilter", filters=[AndUserFilterModelFiltersInner(filter._to_model()) for filter in self.filters])
