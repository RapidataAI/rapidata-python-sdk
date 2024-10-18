from typing import Any
from rapidata.rapidata_client.filter.base_filter import Filter
from rapidata.api_client.models.language_user_filter_model import (
    LanguageUserFilterModel,
)


class LanguageFilter(Filter):

    def __init__(self, language_codes: list[str]):
        # check that all characters in the language codes are lowercase
        if not all([code.islower() for code in language_codes]):
            raise ValueError("Language codes must be lowercase")

        self.languages = language_codes

    def to_model(self):
        return LanguageUserFilterModel(_t="LanguageFilter", languages=self.languages)
