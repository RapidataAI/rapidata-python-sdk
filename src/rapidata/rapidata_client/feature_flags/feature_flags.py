from rapidata.api_client.models.feature_flag_model import FeatureFlagModel


class FeatureFlags:
    """A class to manage feature flags.

    This class provides methods to set and manage various feature flags
    used in the application.

    Attributes:
        _flags (dict[str, str]): A dictionary to store feature flags.
    """

    def __init__(self):
        """Initialize the FeatureFlags object with an empty flags dictionary."""
        self._flags: dict[str, str] = {}

    def to_list(self) -> list[FeatureFlagModel]:
        """Convert the feature flags to a list of FeatureFlagModel objects.

        Returns:
            list[FeatureFlagModel]: A list of FeatureFlagModel objects
                representing the current feature flags.
        """
        return [
            FeatureFlagModel(key=name, value=value)
            for name, value in self._flags.items()
        ]

    def alert_on_fast_response(self, milliseconds: int):
        """Gives an alert as a pop up on the UI when the response time is less than the threshold.

        Args:
            milliseconds (int): if the user responds in less than this time, an alert will be shown.

        Returns:
            FeatureFlags: The current FeatureFlags instance for method chaining.
        """
        if milliseconds < 10:
            print(
                f"Warning: Are you sure you want to set the threshold so low ({milliseconds} milliseconds)?"
            )

        if milliseconds > 30000:
            print(
                f"Warning: Are you sure you want to set the threshold so high ({milliseconds/1000} seconds)?"
            )

        self._flags["alert_on_fast_response"] = str(milliseconds)
        return self

    def disable_translation(self, value: bool = True):
        """Disable automatic translation of all texts in the UI.

        Args:
            value (bool, optional): Whether to disable translation. Defaults to True.

        Returns:
            FeatureFlags: The current FeatureFlags instance for method chaining.
        """
        self._flags["disable_translation"] = str(value)
        return self

    def free_text_minimum_characters(self, value: int):
        """Set the minimum number of characters a user has to type before the task can be successfully submitted.

        Args:
            value (int): The minimum number of characters for free text.

        Returns:
            FeatureFlags: The current FeatureFlags instance for method chaining.
        """
        self._flags["free_text_minimum_characters"] = str(value)
        return self

    def no_shuffle(self, value: bool = True):
        """Only for classify tasks. If true, the order of the categories will be the same as the one in the workflow.

        Args:
            value (bool, optional): Whether to disable shuffling. Defaults to True.

        Returns:
            FeatureFlags: The current FeatureFlags instance for method chaining.
        """
        self._flags["no_shuffle"] = str(value)
        return self

    def compare_with_prompt_design(self, value: bool = True):
        """A special design to compare two texts/images based on a criteria and a given prompt.

        Args:
            value (bool, optional): Whether to enable compare with prompt design. Defaults to True.

        Returns:
            FeatureFlags: The current FeatureFlags instance for method chaining.
        """
        self._flags["claire"] = str(value)
        return self

    def key_value(self, key: str, value: str):
        """Set a custom feature flag with the given key and value. Use this to enable features that do not have a dedicated method (yet).

        Args:
            key (str): The key for the custom feature flag.
            value (str): The value for the custom feature flag.

        Returns:
            FeatureFlags: The current FeatureFlags instance for method chaining.
        """
        self._flags[key] = value
        return self
