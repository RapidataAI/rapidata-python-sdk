from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.rapidata_client.filter.models.demographic_identifier import (
    DemographicIdentifier,
)
from pydantic import BaseModel, ConfigDict


class DemographicFilter(RapidataFilter, BaseModel):
    """DemographicFilter Class

    Filters the graduates of an audience by a demographic attribute (age, gender,
    occupation). Used when deriving a filtered audience from an existing dimension audience
    via :py:meth:`RapidataAudience.filter`.

    Args:
        identifier (DemographicIdentifier): The demographic attribute to filter on.
        values (list[str]): The accepted values for that demographic. A graduate is included
            if any of their stored demographic values for ``identifier`` matches one of these.

    Example:
        ```python
        from rapidata import DemographicFilter, DemographicIdentifier

        # Keep graduates who are between 18 and 39 years old.
        DemographicFilter(DemographicIdentifier.AGE, ["18-29", "30-39"])
        ```
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    identifier: DemographicIdentifier
    values: list[str]

    def __init__(self, identifier: DemographicIdentifier, values: list[str]):
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
                identifier=self.identifier._to_backend_model(),
                values=self.values,
            )
        )
