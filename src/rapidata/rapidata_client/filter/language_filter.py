from typing import Any
from rapidata.rapidata_client.filter._base_filter import RapidataFilter
from rapidata.api_client.models.language_user_filter_model import (
    LanguageUserFilterModel,
)
from pydantic import BaseModel


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

    def _to_model(self):
        return LanguageUserFilterModel(
            _t="LanguageFilter",
            languages=[code.lower() for code in self.language_codes],
        )
