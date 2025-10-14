from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.country_user_filter_model import CountryUserFilterModel
from pydantic import BaseModel, field_validator
from rapidata.rapidata_client.config import logger


class CountryFilter(RapidataFilter, BaseModel):
    """CountryFilter Class

    Can be used to filter who to target based on country codes.

    Args:
        country_codes (list[str]): List of country codes (capitalized) to filter by.
    """

    country_codes: list[str]

    def __init__(self, country_codes: list[str]):
        super().__init__(country_codes=country_codes)

    @field_validator("country_codes")
    @classmethod
    def validate_country_codes(cls, codes: list[str]) -> list[str]:
        validated = []
        for code in codes:
            if len(code) != 2:
                raise ValueError(
                    f"Country codes must be length 2. Invalid code: '{code}'"
                )
            if code != code.upper():
                logger.warning(
                    f"Country code '{code}' should be uppercase. It will be uppercased automatically."
                )
            validated.append(code.upper())
        return validated

    def _to_model(self):
        return CountryUserFilterModel(_t="CountryFilter", countries=self.country_codes)
