from __future__ import annotations

from rapidata.rapidata_client.filter._base_filter import RapidataFilter
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
        from rapidata.api_client.models.i_user_filter_model import IUserFilterModel
        from rapidata.api_client.models.i_user_filter_model_language_user_filter_model import (
            IUserFilterModelLanguageUserFilterModel,
        )

        return IUserFilterModel(
            actual_instance=IUserFilterModelLanguageUserFilterModel(
                _t="LanguageFilter",
                languages=self.language_codes,
            )
        )

    def _to_audience_model(self):
        from rapidata.api_client.models.i_audience_filter import IAudienceFilter
        from rapidata.api_client.models.i_audience_filter_language_audience_filter import (
            IAudienceFilterLanguageAudienceFilter,
        )

        return IAudienceFilter(
            actual_instance=IAudienceFilterLanguageAudienceFilter(
                _t="LanguageFilter", languages=self.language_codes
            )
        )
