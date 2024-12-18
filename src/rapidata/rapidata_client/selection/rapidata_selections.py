from rapidata.rapidata_client.selection import (
    DemographicSelection, 
    LabelingSelection, 
    ValidationSelection, 
    ConditionalValidationSelection, 
    CappedSelection)

class RapidataSelections:
    """RapidataSelections Classes

    Attributes:
        demographic (DemographicSelection): The DemographicSelection instance.
        labeling (LabelingSelection): The LabelingSelection instance.
        validation (ValidationSelection): The ValidationSelection instance.
        conditional_validation (ConditionalValidationSelection): The ConditionalValidationSelection instance.
        capped (CappedSelection): The CappedSelection instance."""
    demographic = DemographicSelection
    labeling = LabelingSelection
    validation = ValidationSelection
    conditional_validation = ConditionalValidationSelection
    capped = CappedSelection
