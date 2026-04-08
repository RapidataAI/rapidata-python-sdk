from __future__ import annotations

from rapidata.rapidata_client.settings._rapidata_setting import RapidataSetting


class PlayPercentageVideoSetting(RapidataSetting):
    """
    Requires users to watch a certain percentage of the video before they can submit their answer.

    Args:
        percentage (int): The percentage of the video that must be played before the user can submit. Must be between 0 and 95.
    """

    def __init__(self, percentage: int = 95):
        if percentage <= 0 or percentage >= 95:
            raise ValueError("The percentage must be between 0 and 95.")

        super().__init__(key="media_played_percentage", value=percentage)
