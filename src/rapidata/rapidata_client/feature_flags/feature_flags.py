from rapidata.api_client.models.feature_flag_model import FeatureFlagModel


class FeatureFlags:
    def __init__(self):
        self._flags: dict[str, str] = {}

    def to_list(self) -> list[FeatureFlagModel]:
        return [FeatureFlagModel(key=name, value=value) for name, value in self._flags.items()]

    def alert_on_fast_response(self, value: int):
        self._flags["alert_on_fast_response"] = str(value)
        return self

    def disable_translation(self, value: bool = True):
        self._flags["disable_translation"] = str(value)
        return self

    def free_text_minimum_characters(self, value: int):
        self._flags["free_text_minimum_characters"] = str(value)
        return self

    def no_shuffle(self, value: bool = True):
        self._flags["no_shuffle"] = str(value)
        return self
    
    def claire_design(self, value: bool = True):
        self._flags["claire"] = str(value)
        return self
    
    def key_value(self, key: str, value: str):
        self._flags[key] = value
        return self
