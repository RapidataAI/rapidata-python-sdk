from __future__ import annotations
from pydantic import BaseModel
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.feature_flag import FeatureFlag
    from rapidata.api_client.models.feature_flag_model import FeatureFlagModel


class RapidataSetting(BaseModel):
    """Base class for all settings"""

    key: str
    value: Any

    def _to_feature_flag(self) -> FeatureFlag:
        from rapidata.api_client.models.feature_flag import FeatureFlag

        return FeatureFlag(key=self.key, value=str(self.value))

    def _to_feature_flag_model(self) -> FeatureFlagModel:
        from rapidata.api_client.models.feature_flag_model import FeatureFlagModel

        return FeatureFlagModel(key=self.key, value=str(self.value))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(key='{self.key}', value={self.value})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(key={self.key!r}, value={self.value!r})"
