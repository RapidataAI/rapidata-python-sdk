from __future__ import annotations

import warnings

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting
from rapidata.rapidata_client.config import managed_print


class FreeTextMinimumCharactersSetting(RapidataSetting):
    """
    Set the minimum number of characters a user has to type.

    Args:
        value (int): The minimum number of characters for free text.
    """

    def __init__(self, value: int):
        if value < 1:
            raise ValueError(
                "The minimum number of characters must be greater than or equal to 1."
            )
        if value > 40:
            managed_print(
                f"Warning: Are you sure you want to set the minimum number of characters at {value}?"
            )
        super().__init__(key="free_text_minimum_characters", value=value)


class FreeTextMinimumCharacters(FreeTextMinimumCharactersSetting):
    """Deprecated: Use :class:`FreeTextMinimumCharactersSetting` instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "FreeTextMinimumCharacters is deprecated, use FreeTextMinimumCharactersSetting instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
