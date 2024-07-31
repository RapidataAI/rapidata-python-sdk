class FeatureFlags:
    def __init__(self):
        self._flags: dict[str, str] = {}

    def to_list(self) -> list[dict[str, str]]:
        # transform dict of flags to list of flags
        return [{"name": name, "value": value} for name, value in self._flags.items()]
    
    def alert_on_fast_response(self, value: int):
        self._flags["alertOnFastResponse"] = str(value)
        return self
    
    def disable_translation(self, value: bool):
        self._flags["disableTranslation"] = str(value)
        return self
    
    