from pydantic import BaseModel
from enum import Enum
from typing import Any
from rapidata.api_client.models.feature_flag_model import FeatureFlagModel


class TranslationBehaviour(Enum):
    BOTH = "both"
    ONLY_ORIGINAL = "only original"
    ONLY_TRANSLATED = "only translated"

class RapidataSetting(BaseModel):
    """Base class for all settings"""
    key: str
    value: Any

    def to_feature_flag(self) -> FeatureFlagModel:
        return FeatureFlagModel(key=self.key, value=str(self.value))

def alert_on_fast_response(milliseconds: int) -> RapidataSetting:
    """Gives an alert as a pop up on the UI when the response time is less than the threshold."""
    if not isinstance(milliseconds, int):
        raise ValueError("The alert must be an integer.")
    if milliseconds < 10:
        print(f"Warning: Are you sure you want to set the threshold so low ({milliseconds} milliseconds)?")
    if milliseconds > 30000:
        print(f"Warning: Are you sure you want to set the threshold so high ({round(milliseconds/1000, 2)} seconds)?")
    if milliseconds < 0:
        raise ValueError("The alert must be greater than or equal to 0.")
    
    return RapidataSetting(key="alert_on_fast_response", value=milliseconds)

def translation_behaviour(behaviour: TranslationBehaviour = TranslationBehaviour.BOTH) -> RapidataSetting:
    """Defines what's the behaviour of the translation in the UI."""
    if not isinstance(behaviour, TranslationBehaviour):
        raise ValueError("The behaviour must be a TranslationBehaviour.")
    
    return RapidataSetting(key="translation_behaviour", value=behaviour.value)

def free_text_minimum_characters(value: int) -> RapidataSetting:
    """Set the minimum number of characters a user has to type."""
    if value < 0:
        raise ValueError("The minimum number of characters must be greater than or equal to 0.")
    if value > 20:
        print(f"Warning: Are you sure you want to set the minimum number of characters at {value}?")
    return RapidataSetting(key="free_text_minimum_characters", value=value)

def no_shuffle(value: bool = True) -> RapidataSetting:
    """Only for classify tasks. If true, the order of the categories will be the same."""
    if not isinstance(value, bool):
        raise ValueError("The value must be a boolean.")
    
    return RapidataSetting(key="no_shuffle", value=value)

def play_video_until_the_end(additional_time: int = 0) -> RapidataSetting:
    """Allows users to only answer once the video has finished playing.
    Parameters:
        additional_time (int): The additional time (ms) to wait after the video has finished playing. \
            Can be negative to allow users to answer before the video has finished playing.
    """
    if additional_time < -25000 or additional_time > 25000:
        raise ValueError("The additional time must be between -25000 and 25000.")
    
    return RapidataSetting(key="alert_on_fast_response_add_media_duration", value=additional_time)

def custom_setting(key: str, value: str) -> RapidataSetting:
    """Set a custom setting with the given key and value."""
    if not isinstance(key, str):
        raise ValueError("The key must be a string.")
    
    return RapidataSetting(key=key, value=value)

class RapidataSettings:
    """Container class for all setting factory functions"""
    alert_on_fast_response = staticmethod(alert_on_fast_response)
    translation_behaviour = staticmethod(translation_behaviour)
    free_text_minimum_characters = staticmethod(free_text_minimum_characters)
    no_shuffle = staticmethod(no_shuffle)
    play_video_until_the_end = staticmethod(play_video_until_the_end)
    custom_setting = staticmethod(custom_setting)
