from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.age_user_filter_model import AgeUserFilterModel
from rapidata.api_client.models.age_group import AgeGroup


class AgeFilter(Filter):

    def __init__(self, age_groups: list[AgeGroup]):
        self.age_groups = age_groups

    def to_model(self):
        return AgeUserFilterModel(
            _t="AgeFilter",
            ageGroups=self.age_groups,
        )
