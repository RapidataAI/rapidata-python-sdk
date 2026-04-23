from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.feature_flag import FeatureFlag


FeatureFlagTarget = Literal["rapids", "campaign"]


class RapidataSetting(BaseModel):
    """Base class for all settings.

    Every setting is translated into a feature flag when sent to the API.
    The ``target`` attribute determines whether the resulting feature flag is
    attached to the rapid level (``rapidFeatureFlags``) or the campaign level
    (``campaignFeatureFlags``) during order and job creation. Subclasses that
    represent rapid-level behaviour (the default) should leave ``target`` at
    ``"rapids"``. Only :class:`CustomSetting` exposes ``target`` as an
    argument so users can opt into campaign-level flags.
    """

    key: str
    value: Any
    target: FeatureFlagTarget = "rapids"

    def _to_feature_flag(self) -> FeatureFlag:
        from rapidata.api_client.models.feature_flag import FeatureFlag

        return FeatureFlag(key=self.key, value=str(self.value))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(key='{self.key}', value={self.value}, target='{self.target}')"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(key={self.key!r}, value={self.value!r}, "
            f"target={self.target!r})"
        )
