from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.api_client.models.conditional_validation_rapid_selection_config import (
    ValidationChance,
)
from rapidata.api_client.models.conditional_validation_selection import (
    ConditionalValidationSelection as ConditionalValidationSelectionModel,
)


class ConditionalValidationSelection(RapidataSelection):
    """Conditional validation selection class.

    Probabilistically decides how many validation rapids you want to show per session based on the user score.
    
    Args:
        validation_set_id (str): The id of the validation set to be used.
        thresholds (list[float]): The thresholds to use for the user score.
        chances (list[float]): The chances of showing a validation rapid for each threshold.
        rapid_counts (list[int]): The amount of validation rapids that will be shown per session of this validation set for each threshold if selected by probability. (all or nothing)
    """

    def __init__(
        self,
        validation_set_id: str,
        thresholds: list[float],
        chances: list[float],
        rapid_counts: list[int],
    ):
        if len(thresholds) != len(chances) or len(thresholds) != len(rapid_counts):
            raise ValueError(
                "The lengths of thresholds, chances and rapid_counts must be equal."
            )
        self.validation_set_id = validation_set_id
        self.thresholds = thresholds
        self.chances = chances
        self.rapid_counts = rapid_counts

    def _to_model(self):
        return ConditionalValidationSelectionModel(
            _t="ConditionalValidationSelection",
            validationSetId=self.validation_set_id,
            validationChances=[
                ValidationChance(
                    userScoreThreshold=threshold, chance=chance, rapidCount=rapid_count
                )
                for threshold, chance, rapid_count in zip(
                    self.thresholds, self.chances, self.rapid_counts
                )
            ],
        )
