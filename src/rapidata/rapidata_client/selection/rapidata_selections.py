from rapidata.rapidata_client.selection import (
    DemographicSelection, 
    LabelingSelection, 
    ValidationSelection, 
    ConditionalValidationSelection, 
    CappedSelection)

class RapidataSelections:
    """RapidataSelections Classes

    Selections are used to define what type of tasks and in what order they are shown to the user.

    Attributes:
        labeling (LabelingSelection): The LabelingSelection instance.
        validation (ValidationSelection): The ValidationSelection instance.
        conditional_validation (ConditionalValidationSelection): The ConditionalValidationSelection instance.
        demographic (DemographicSelection): The DemographicSelection instance.
        capped (CappedSelection): The CappedSelection instance."""
    labeling = LabelingSelection
    validation = ValidationSelection
    conditional_validation = ConditionalValidationSelection
    demographic = DemographicSelection
    capped = CappedSelection
