from rapidata.api_client.models.feature_flag_model import FeatureFlagModel
from enum import Enum

class TranslationBehaviour(Enum):
    BOTH = "both"
    ONLY_ORIGINAL = "only original"
    ONLY_TRANSLATED = "only translated"


class Settings:
    """A class to manage settings.

    This class provides methods to set and manage various settings
    used in the application.

    Attributes:
        _settings (dict[str, str]): A dictionary to store settings.
    """

    def __init__(self):
        """Initialize the Settings object with an empty flags dictionary."""
        self._settings: dict[str, str] = {}

    def to_list(self) -> list[FeatureFlagModel]:
        """Convert the settings to a list of FeatureFlagModel objects.

        Returns:
            list[FeatureFlagModel]: A list of FeatureFlagModel objects
                representing the current settings.
        """
        return [
            FeatureFlagModel(key=name, value=value)
            for name, value in self._settings.items()
        ]

    def alert_on_fast_response(self, milliseconds: int):
        """Gives an alert as a pop up on the UI when the response time is less than the threshold.

        Args:
            milliseconds (int): if the user responds in less than this time, an alert will be shown.

        Returns:
            Settings: The current Settings instance for method chaining.
        """
        if milliseconds < 10:
            print(
                f"Warning: Are you sure you want to set the threshold so low ({milliseconds} milliseconds)?"
            )

        if milliseconds > 30000:
            print(
                f"Warning: Are you sure you want to set the threshold so high ({milliseconds/1000} seconds)?"
            )

        self._settings["alert_on_fast_response"] = str(milliseconds)
        return self


    def translation_behaviour(self, behaviour: TranslationBehaviour = TranslationBehaviour.BOTH):
        """Defines what's the behaviour of the translation in the UI.

        The behaviour can be set to:
            - TranslationBehaviour.BOTH: Show both the original and the translated text.
            - TranslationBehaviour.ONLY_ORIGINAL: Show only the original text.
            - TranslationBehaviour.ONLY_TRANSLATED: Show only the translated text.

        Args:
            behaviour (TranslationBehaviour): The translation behaviour. Defaults to TranslationBehaviour.BOTH.

        Returns:
            Settings: The current Settings instance for method chaining.
        """
        self._settings["translation_behaviour"] = behaviour.value
        return self

    def free_text_minimum_characters(self, value: int):
        """Set the minimum number of characters a user has to type before the task can be successfully submitted.

        Args:
            value (int): The minimum number of characters for free text.

        Returns:
            Settings: The current Settings instance for method chaining.
        """
        self._settings["free_text_minimum_characters"] = str(value)
        return self

    def no_shuffle(self, value: bool = True):
        """Only for classify tasks. If true, the order of the categories will be the same as the one in the workflow.

        Args:
            value (bool, optional): Whether to disable shuffling. Defaults to True.

        Returns:
            Settings: The current Settings instance for method chaining.
        """
        self._settings["no_shuffle"] = str(value)
        return self

    def compare_with_prompt_design(self, value: bool = True):
        """A special design to compare two texts/images based on a criteria and a given prompt.

        Args:
            value (bool, optional): Whether to enable compare with prompt design. Defaults to True.

        Returns:
            Settings: The current Settings instance for method chaining.
        """
        self._settings["claire"] = str(value)
        return self

    def key_value(self, key: str, value: str):
        """Set a custom setting with the given key and value. Use this to enable features that do not have a dedicated method (yet).

        Args:
            key (str): The key for the custom setting.
            value (str): The value for the custom setting.

        Returns:
            Settings: The current Settings instance for method chaining.
        """
        self._settings[key] = value
        return self
