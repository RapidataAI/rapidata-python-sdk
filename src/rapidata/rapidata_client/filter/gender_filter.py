from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.gender_user_filter_model import GenderUserFilterModel
from rapidata.api_client.models.gender import Gender


class GenderFilter(Filter):

    def __init__(self, genders: list[str]):
        # check that all the age groups exist in the AgeGroup enum
        for gender in genders:
            if gender not in Gender:
                raise ValueError(
                    f"Invalid gender {Gender}, available gender groups are {[g.value for g in Gender]}"
                )

        self.genders = [Gender(gender) for gender in Gender]

    def to_model(self) -> Any:
        return GenderUserFilterModel(
            _t="GenderFilter",
            genders=self.genders,
        )
