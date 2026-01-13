from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
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
        from rapidata.api_client.models.i_user_filter_model import IUserFilterModel
        from rapidata.api_client.models.i_user_filter_model_not_user_filter_model import (
            IUserFilterModelNotUserFilterModel,
        )

        return IUserFilterModel(
            actual_instance=IUserFilterModelNotUserFilterModel(
                _t="NotFilter",
                filter=self.filter._to_model(),
            )
        )

    def _to_audience_model(self):
        from rapidata.api_client.models.i_audience_filter import IAudienceFilter
        from rapidata.api_client.models.i_audience_filter_not_audience_filter import (
            IAudienceFilterNotAudienceFilter,
        )

        return IAudienceFilter(
            actual_instance=IAudienceFilterNotAudienceFilter(
                _t="NotFilter", filter=self.filter._to_audience_model()
            )
        )
