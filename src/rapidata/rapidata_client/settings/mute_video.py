from __future__ import annotations

import warnings

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class MuteVideoSetting(RapidataSetting):
    """
    Mute the video. If this setting is not supplied, the video will not be muted.

    Args:
        value (bool): Whether to mute the video. Defaults to True.
    """

    def __init__(self, value: bool = True):
        if not isinstance(value, bool):
            raise ValueError("The value must be a boolean.")
        super().__init__(key="mute_video_asset", value=value)


class MuteVideo(MuteVideoSetting):
    """Deprecated: Use :class:`MuteVideoSetting` instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "MuteVideo is deprecated, use MuteVideoSetting instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
