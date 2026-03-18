from __future__ import annotations

import warnings

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting
from rapidata.rapidata_client.config import managed_print


class AlertOnFastResponseSetting(RapidataSetting):
    """
    Gives an alert as a pop up on the UI when the response time is less than the milliseconds.

    Args:
        threshold (int): if the user responds in less than this time, an alert will be shown.
    """

    def __init__(self, threshold: int):
        if not isinstance(threshold, int):
            raise ValueError("The alert must be an integer.")
        if threshold < 10:
            managed_print(
                f"Warning: Are you sure you want to set the threshold so low ({threshold} milliseconds)?"
            )
        if threshold > 25000:
            raise ValueError("The alert must be less than 25000 milliseconds.")
        if threshold < 0:
            raise ValueError("The alert must be greater than or equal to 0.")

        super().__init__(key="alert_on_fast_response", value=threshold)


class AlertOnFastResponse(AlertOnFastResponseSetting):
    """Deprecated: Use :class:`AlertOnFastResponseSetting` instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "AlertOnFastResponse is deprecated, use AlertOnFastResponseSetting instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
