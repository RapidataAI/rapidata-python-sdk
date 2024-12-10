from typing import Any
from rapidata.rapidata_client.filter.base_filter import RapidataFilter
from rapidata.api_client.models.language_user_filter_model import (
    LanguageUserFilterModel,
)


class LanguageFilter(RapidataFilter):
    """LanguageFilter Class
    
    Can be used to filter who to target based on language codes."""
    def __init__(self, language_codes: list[str]):
        """
        Initialize a LanguageFilter instance.

        Args:
            language_codes (list[str]): List of language codes to filter by.
        """
        if not isinstance(language_codes, list):
            raise ValueError("Language codes must be a list")
        
        # check that all characters in the language codes are lowercase
        if not all([code.islower() for code in language_codes]):
            raise ValueError("Language codes must be lowercase")
        
        for code in language_codes:
            if not len(code) == 2:
                raise ValueError("Language codes must be two characters long")

        self.languages = language_codes

    def to_model(self):
        return LanguageUserFilterModel(_t="LanguageFilter", languages=self.languages)
