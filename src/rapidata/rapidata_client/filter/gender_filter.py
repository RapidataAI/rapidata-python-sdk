from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.gender_user_filter_model import GenderUserFilterModel
from rapidata.api_client.models.gender import Gender


class GenderFilter(Filter):

    def __init__(self, genders: list[Gender]):
        self.genders = genders

    def to_model(self):
        return GenderUserFilterModel(
            _t="GenderFilter",
            genders=self.genders,
        )
