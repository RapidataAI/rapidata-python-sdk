from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.country_user_filter_model import CountryUserFilterModel


class CountryFilter(RapidataFilter):
    """CountryFilter Class

    Can be used to filter who to target based on country codes.
    
    Args:
        country_codes (list[str]): List of country codes (capizalized) to filter by.
    """

    def __init__(self, country_codes: list[str]):
        # check that all characters in the country codes are uppercase
        if not isinstance(country_codes, list):
            raise ValueError("Country codes must be a list")
        
        if not all([code.isupper() for code in country_codes]):
            raise ValueError("Country codes must be uppercase")

        self.country_codes = country_codes

    def _to_model(self):
        return CountryUserFilterModel(_t="CountryFilter", countries=self.country_codes)
