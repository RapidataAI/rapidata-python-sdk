from __future__ import annotations

import inspect

import pytest

from rapidata import MuteVideoSetting, RapidataSettings
from rapidata.api_client.models.feature_flag import FeatureFlag
from rapidata.rapidata_client.settings import RapidataSetting

FLAG_SETTINGS = [
    cls
    for cls in vars(RapidataSettings).values()
    if isinstance(cls, type)
    and issubclass(cls, RapidataSetting)
    and list(inspect.signature(cls.__init__).parameters) == ["self"]
]


def test_flag_settings_are_discovered() -> None:
    assert MuteVideoSetting in FLAG_SETTINGS


@pytest.mark.parametrize("setting", FLAG_SETTINGS, ids=lambda cls: cls.__name__)
def test_flag_setting_sends_lowercase_true(setting: type[RapidataSetting]) -> None:
    instance = setting()

    assert instance._to_feature_flag() == FeatureFlag(key=instance.key, value="true")


@pytest.mark.parametrize("value", [True, False, "true"])
@pytest.mark.parametrize("setting", FLAG_SETTINGS, ids=lambda cls: cls.__name__)
def test_flag_setting_rejects_positional_value(
    setting: type[RapidataSetting], value: object
) -> None:
    with pytest.raises(TypeError):
        setting(value)  # type: ignore[call-arg]


@pytest.mark.parametrize("setting", FLAG_SETTINGS, ids=lambda cls: cls.__name__)
def test_flag_setting_rejects_keyword_value(setting: type[RapidataSetting]) -> None:
    with pytest.raises(TypeError):
        setting(value=False)  # type: ignore[call-arg]
