from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from pydantic import BaseModel, ConfigDict


class AndFilter(RapidataFilter, BaseModel):
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

    model_config = ConfigDict(arbitrary_types_allowed=True)

    filters: list[RapidataFilter]

    def __init__(self, filters: list[RapidataFilter]):
        super().__init__(filters=filters)

    def _to_model(self):
        from rapidata.api_client.models.i_user_filter_model import IUserFilterModel
        from rapidata.api_client.models.i_user_filter_model_and_user_filter_model import (
            IUserFilterModelAndUserFilterModel,
        )

        return IUserFilterModel(
            actual_instance=IUserFilterModelAndUserFilterModel(
                _t="AndFilter",
                filters=[filter._to_model() for filter in self.filters],
            )
        )

    def _to_audience_model(self):
        from rapidata.api_client.models.i_audience_filter import IAudienceFilter
        from rapidata.api_client.models.i_audience_filter_and_audience_filter import (
            IAudienceFilterAndAudienceFilter,
        )

        return IAudienceFilter(
            actual_instance=IAudienceFilterAndAudienceFilter(
                _t="AndFilter",
                filters=[filter._to_audience_model() for filter in self.filters],
            ),
        )
