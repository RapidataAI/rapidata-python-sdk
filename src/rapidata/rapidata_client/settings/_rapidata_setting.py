from pydantic import BaseModel
from typing import Any
from rapidata.api_client.models.feature_flag_model import FeatureFlagModel

class RapidataSetting(BaseModel):
    """Base class for all settings"""
    key: str
    value: Any

    def _to_feature_flag(self) -> FeatureFlagModel:
        return FeatureFlagModel(key=self.key, value=str(self.value))
