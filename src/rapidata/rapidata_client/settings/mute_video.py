from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class MuteVideo(RapidataSetting):
    """
    Mute the video. If this setting is not supplied, the video will not be muted.

    Args:
        value (bool): Whether to mute the video. Defaults to True.
    """

    def __init__(self, value: bool = True):
        if not isinstance(value, bool):
            raise ValueError("The value must be a boolean.")
        super().__init__(key="mute_video_asset", value=value)
