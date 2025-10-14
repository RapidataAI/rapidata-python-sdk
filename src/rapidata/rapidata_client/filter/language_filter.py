from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.language_user_filter_model import (
    LanguageUserFilterModel,
)
from pydantic import BaseModel, field_validator
from rapidata.rapidata_client.config import logger


class LanguageFilter(RapidataFilter, BaseModel):
    """LanguageFilter Class

    Can be used to filter who to target based on language codes.

    Args:
        language_codes (list[str]): List of language codes to filter by.

    Example:
        ```python
        LanguageFilter(["en", "de"])
        ```
        This will limit the order to be shown to only people who have their phone set to english or german
    """

    language_codes: list[str]

    def __init__(self, language_codes: list[str]):
        super().__init__(language_codes=language_codes)

    @field_validator("language_codes")
    @classmethod
    def validate_language_codes(cls, codes: list[str]) -> list[str]:
        validated = []
        for code in codes:
            if len(code) != 2:
                raise ValueError(
                    f"Language codes must be length 2. Invalid code: '{code}'"
                )
            if code != code.lower():
                logger.warning(
                    f"Language code '{code}' should be lowercase. It will be lowercased automatically."
                )
            validated.append(code.lower())
        return validated

    def _to_model(self):
        return LanguageUserFilterModel(
            _t="LanguageFilter",
            languages=self.language_codes,
        )
