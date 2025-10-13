from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.country_user_filter_model import CountryUserFilterModel
from pydantic import BaseModel


class CountryFilter(RapidataFilter, BaseModel):
    """CountryFilter Class

    Can be used to filter who to target based on country codes.

    Args:
        country_codes (list[str]): List of country codes (capitalized) to filter by.
    """

    country_codes: list[str]

    def _to_model(self):
        return CountryUserFilterModel(
            _t="CountryFilter", countries=[code.upper() for code in self.country_codes]
        )
