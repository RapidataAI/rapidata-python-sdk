from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.rapidata_client.filter.models.age_group import AgeGroup
from pydantic import BaseModel, ConfigDict


class AgeFilter(RapidataFilter, BaseModel):
    """AgeFilter Class

    Can be used to filter who to target based on age groups.

    Args:
        age_groups (list[AgeGroup]): List of age groups to filter by."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    age_groups: list[AgeGroup]

    def __init__(self, age_groups: list[AgeGroup]):
        super().__init__(age_groups=age_groups)

    def _to_model(self):
        from rapidata.api_client.models.i_user_filter_model import IUserFilterModel
        from rapidata.api_client.models.i_user_filter_model_age_user_filter_model import (
            IUserFilterModelAgeUserFilterModel,
        )

        return IUserFilterModel(
            actual_instance=IUserFilterModelAgeUserFilterModel(
                _t="AgeFilter",
                ageGroups=[
                    age_group._to_backend_model() for age_group in self.age_groups
                ],
            )
        )

    def _to_audience_model(self):
        raise NotImplementedError("AgeFilter is not supported for audiences")
