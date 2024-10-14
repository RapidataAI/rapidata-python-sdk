from rapidata.rapidata_client.selection.base_selection import Selection
from rapidata.api_client.models.demographic_selection import (
    DemographicSelection as DemographicSelectionModel,
)
from rapidata.api_client.models.conditional_validation_rapid_selection_config import (
    ValidationChance,
)

from rapidata.api_client.models.conditional_validation_selection import (
    ConditionalValidationSelection,
)


class ConditionalValidationRapidSelection(Selection):
    """Demographic selection class."""

    def __init__(
        self,
        validation_set_id: str,
        thresholds: list[float],
        chances: list[float],
        rapid_counts: list[int],
    ):
        self.validation_set_id = validation_set_id
        self.thresholds = thresholds
        self.chances = chances
        self.rapid_counts = rapid_counts

    def to_model(self):
        return ConditionalValidationSelection(
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
