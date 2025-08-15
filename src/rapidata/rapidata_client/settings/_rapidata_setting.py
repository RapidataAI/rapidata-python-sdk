from pydantic import BaseModel
from typing import Any
from rapidata.api_client.models.feature_flag_model import FeatureFlagModel


class RapidataSetting(BaseModel):
    """Base class for all settings"""

    key: str
    value: Any

    def _to_feature_flag(self) -> FeatureFlagModel:
        return FeatureFlagModel(key=self.key, value=str(self.value))

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(key='{self.key}', value={self.value})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(key={self.key!r}, value={self.value!r})"
