from abc import ABC
from typing import Any

from rapidata.rapidata_client.workflow.feature_flags import FeatureFlags
from rapidata.rapidata_client.workflow.referee.base_referee import Referee
from rapidata.rapidata_client.workflow.referee.naive_referee import NaiveReferee


class Workflow(ABC):
    
    def __init__(self, type: str):
        self._type = type
        self._referee = NaiveReferee()
        self._target_country_codes: list[str] = []
        self._feature_flags: FeatureFlags = FeatureFlags()

    def to_dict(self) -> dict[str, Any]:
        return {
            "_t": self._type,
            "referee": self._referee.to_dict(),
            "targetCountryCodes": self._target_country_codes,
            "featureFlags": self._feature_flags.to_list(),
        }

    def referee(self, referee: Referee):
        self._referee = referee
        return self
    
    def target_country_codes(self, target_country_codes: list[str]):
        self._target_country_codes = target_country_codes
        return self
    
    def feature_flags(self, feature_flags: FeatureFlags):
        self._feature_flags = feature_flags
        return self