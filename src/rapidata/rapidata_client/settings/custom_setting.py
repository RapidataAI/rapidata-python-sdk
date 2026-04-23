from __future__ import annotations

from typing import get_args

from rapidata.rapidata_client.settings._rapidata_setting import (
    FeatureFlagTarget,
    RapidataSetting,
)


class CustomSetting(RapidataSetting):
    """
    Set a custom setting with the given key and value. Use this to enable features that do not have a dedicated method (yet).

    Args:
        key (str): The key for the custom setting.
        value (str): The value for the custom setting.
        target (Literal["rapids", "campaign"], optional): Whether the feature flag should be applied
            at the rapid level or the campaign level. Defaults to ``"rapids"``.
    """

    def __init__(
        self,
        key: str,
        value: str,
        target: FeatureFlagTarget = "rapids",
    ):
        if not isinstance(key, str):
            raise ValueError("The key must be a string.")

        valid_targets = get_args(FeatureFlagTarget)
        if target not in valid_targets:
            raise ValueError(
                f"The target must be one of {valid_targets}, got {target!r}."
            )

        super().__init__(key=key, value=value, target=target)
