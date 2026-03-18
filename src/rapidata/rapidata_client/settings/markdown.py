from __future__ import annotations

import warnings

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class MarkdownSetting(RapidataSetting):
    """
    Enables limited markdown rendering for text datapoints.
    Useful when comparing formatted text like LLM outputs.

    Args:
        value (bool): Whether to enable markdown rendering. Defaults to True.
    """

    def __init__(self, value: bool = True):
        if not isinstance(value, bool):
            raise ValueError("The value must be a boolean.")
        super().__init__(key="use_text_asset_markdown", value=value)


class Markdown(MarkdownSetting):
    """Deprecated: Use :class:`MarkdownSetting` instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Markdown is deprecated, use MarkdownSetting instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
