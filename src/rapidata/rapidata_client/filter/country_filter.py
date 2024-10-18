from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.country_user_filter_model import CountryUserFilterModel


class CountryFilter(Filter):

    def __init__(self, country_codes: list[str]):
        # check that all characters in the country codes are uppercase
        if not all([code.isupper() for code in country_codes]):
            raise ValueError("Country codes must be uppercase")

        self.country_codes = country_codes

    def to_model(self):
        return CountryUserFilterModel(_t="CountryFilter", countries=self.country_codes)
