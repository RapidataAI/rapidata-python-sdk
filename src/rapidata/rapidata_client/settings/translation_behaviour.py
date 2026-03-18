from __future__ import annotations

import warnings

from rapidata.rapidata_client.settings.models.translation_behaviour_options import (
    TranslationBehaviourOptions,
)
from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class TranslationBehaviourSetting(RapidataSetting):
    """
    Defines what's the behaviour of the translation in the UI.
    Will not translate text datapoints or sentences.

    Args:
        value (TranslationBehaviourOptions): The translation behaviour.
    """

    def __init__(self, value: TranslationBehaviourOptions):
        if not isinstance(value, TranslationBehaviourOptions):
            raise ValueError("The value must be a TranslationBehaviourOptions.")

        super().__init__(key="translation_behaviour", value=value.value)


class TranslationBehaviour(TranslationBehaviourSetting):
    """Deprecated: Use :class:`TranslationBehaviourSetting` instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "TranslationBehaviour is deprecated, use TranslationBehaviourSetting instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
