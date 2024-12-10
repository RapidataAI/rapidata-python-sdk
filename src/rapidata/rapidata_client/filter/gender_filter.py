from typing import Any
from rapidata.rapidata_client.filter.base_filter import RapidataFilter
from rapidata.api_client.models.gender_user_filter_model import GenderUserFilterModel
from rapidata.api_client.models.gender import Gender


class GenderFilter(RapidataFilter):
    """GenderFilter Class
    
    Can be used to filter who to target based on their gender."""

    def __init__(self, genders: list[Gender]):
        """
        Initialize a GenderFilter instance.

        Args:
            genders (list[Gender]): List of genders to filter by.
        """
        self.genders = genders

    def to_model(self):
        return GenderUserFilterModel(
            _t="GenderFilter",
            genders=self.genders,
        )
