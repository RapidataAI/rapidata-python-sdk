from typing import Any
from rapidata.rapidata_client.filter.base_filter import RapidataFilter
from rapidata.api_client.models.age_user_filter_model import AgeUserFilterModel
from rapidata.api_client.models.age_group import AgeGroup


class AgeFilter(RapidataFilter):
    """AgeFilter Class
    
    Can be used to filter who to target based on age groups."""

    def __init__(self, age_groups: list[AgeGroup]):
        """
        Initialize an AgeFilter instance.

        Args:
            age_groups (list[AgeGroup]): List of age groups to filter by.
        """
        self.age_groups = age_groups

    def to_model(self):
        return AgeUserFilterModel(
            _t="AgeFilter",
            ageGroups=self.age_groups,
        )
