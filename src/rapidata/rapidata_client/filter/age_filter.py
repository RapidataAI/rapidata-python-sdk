from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.age_user_filter_model import AgeUserFilterModel
from rapidata.rapidata_client.filter.models.age_group import AgeGroup


class AgeFilter(RapidataFilter):
    """AgeFilter Class
    
    Can be used to filter who to target based on age groups.
    
    
    Args:
        age_groups (list[AgeGroup]): List of age groups to filter by."""

    def __init__(self, age_groups: list[AgeGroup]):
        self.age_groups = age_groups

    def _to_model(self):
        return AgeUserFilterModel(
            _t="AgeFilter",
            ageGroups=[age_group._to_backend_model() for age_group in self.age_groups],
        )
