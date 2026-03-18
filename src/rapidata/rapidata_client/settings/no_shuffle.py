from __future__ import annotations

import warnings

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class NoShuffleSetting(RapidataSetting):
    """
    Only for classification and compare tasks. If true, the order of the categories / images will not be shuffled and presented in the same order as specified.

    If this is not added to the order, the shuffling will be active.

    Args:
        value (bool, optional): Whether to disable shuffling. Defaults to True for function call.
    """

    def __init__(self, value: bool = True):
        if not isinstance(value, bool):
            raise ValueError("The value must be a boolean.")

        super().__init__(key="no_shuffle", value=value)


class NoShuffle(NoShuffleSetting):
    """Deprecated: Use :class:`NoShuffleSetting` instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "NoShuffle is deprecated, use NoShuffleSetting instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
