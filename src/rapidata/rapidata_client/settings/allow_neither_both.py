from __future__ import annotations

import warnings

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class AllowNeitherBothSetting(RapidataSetting):
    """
    Set whether to allow neither or both options.
    This setting only works for compare orders.

    Args:
        value (bool): Whether to allow neither or both options. Defaults to True.
            If this setting is not added to an order, the users won't be able to select neither or both.
    """

    def __init__(self, value: bool = True):
        if not isinstance(value, bool):
            raise ValueError("The value must be a boolean.")
        super().__init__(key="compare_unsure", value=value)


class AllowNeitherBoth(AllowNeitherBothSetting):
    """Deprecated: Use :class:`AllowNeitherBothSetting` instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "AllowNeitherBoth is deprecated, use AllowNeitherBothSetting instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
