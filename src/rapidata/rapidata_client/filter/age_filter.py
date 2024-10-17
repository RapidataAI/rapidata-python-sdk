from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.age_user_filter_model import AgeUserFilterModel
from rapidata.api_client.models.age_group import AgeGroup


class AgeFilter(Filter):

    def __init__(self, age_groups: list[str]):
        # check that all the age groups exist in the AgeGroup enum
        for age_group in age_groups:
            if age_group not in AgeGroup:
                raise ValueError(
                    f"Invalid age group {age_group}, available age groups are {[m.value for m in AgeGroup]}"
                )

        self.age_groups = [AgeGroup(age_group) for age_group in age_groups]

    def to_model(self) -> Any:
        return AgeUserFilterModel(
            _t="AgeFilter",
            ageGroups=self.age_groups,
        )
