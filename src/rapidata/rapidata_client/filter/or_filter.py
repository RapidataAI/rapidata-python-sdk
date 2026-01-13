from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from pydantic import BaseModel, ConfigDict


class OrFilter(RapidataFilter, BaseModel):
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

    model_config = ConfigDict(arbitrary_types_allowed=True)

    filters: list[RapidataFilter]

    def __init__(self, filters: list[RapidataFilter]):
        super().__init__(filters=filters)

    def _to_model(self):
        from rapidata.api_client.models.i_user_filter_model import IUserFilterModel
        from rapidata.api_client.models.i_user_filter_model_or_user_filter_model import (
            IUserFilterModelOrUserFilterModel,
        )

        return IUserFilterModel(
            actual_instance=IUserFilterModelOrUserFilterModel(
                _t="OrFilter",
                filters=[filter._to_model() for filter in self.filters],
            )
        )

    def _to_audience_model(self):
        from rapidata.api_client.models.i_audience_filter import IAudienceFilter
        from rapidata.api_client.models.i_audience_filter_or_audience_filter import (
            IAudienceFilterOrAudienceFilter,
        )

        return IAudienceFilter(
            actual_instance=IAudienceFilterOrAudienceFilter(
                _t="OrFilter",
                filters=[filter._to_audience_model() for filter in self.filters],
            )
        )
