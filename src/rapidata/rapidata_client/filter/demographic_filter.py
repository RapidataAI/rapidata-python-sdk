from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from pydantic import BaseModel


class DemographicFilter(RapidataFilter, BaseModel):
    """DemographicFilter Class

    Filters the graduates of an audience by a demographic attribute (e.g. age, gender,
    occupation). Used when deriving a filtered audience from an existing dimension audience
    via :py:meth:`RapidataAudience.filter`.

    Args:
        identifier (str): The demographic key to filter on (e.g. ``"age"``, ``"gender"``,
            ``"occupation"``).
        values (list[str]): The accepted values for that demographic. A graduate is included
            if any of their stored demographic values for ``identifier`` matches one of these.

    Example:
        ```python
        from rapidata import DemographicFilter

        # Keep graduates who are between 18 and 39 years old.
        DemographicFilter("age", ["18-29", "30-39"])
        ```
    """

    identifier: str
    values: list[str]

    def __init__(self, identifier: str, values: list[str]):
        super().__init__(identifier=identifier, values=values)

    def _to_model(self):
        raise NotImplementedError(
            "DemographicFilter only applies to filtered audiences; use AgeFilter / GenderFilter for user-level filters."
        )

    def _to_audience_model(self):
        from rapidata.api_client.models.i_audience_filter import IAudienceFilter
        from rapidata.api_client.models.i_audience_filter_demographic_audience_filter import (
            IAudienceFilterDemographicAudienceFilter,
        )

        return IAudienceFilter(
            actual_instance=IAudienceFilterDemographicAudienceFilter(
                _t="DemographicFilter",
                identifier=self.identifier,
                values=self.values,
            )
        )
