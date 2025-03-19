from rapidata.rapidata_client.selection import (
    DemographicSelection, 
    LabelingSelection, 
    ValidationSelection, 
    ConditionalValidationSelection, 
    CappedSelection,
    ShufflingSelection)

class RapidataSelections:
    """RapidataSelections Classes

    Selections are used to define what type of tasks and in what order they are shown to the user. 
    All Tasks are called a "Session". A session can contain multiple tasks of different types.

    Attributes:
        labeling (LabelingSelection): The LabelingSelection instance.
        validation (ValidationSelection): The ValidationSelection instance.
        conditional_validation (ConditionalValidationSelection): The ConditionalValidationSelection instance.
        demographic (DemographicSelection): The DemographicSelection instance.
        capped (CappedSelection): The CappedSelection instance.
        shuffling (ShufflingSelection): The ShufflingSelection instance.
    
    Example:
        ```python
        from rapidata import LabelingSelection, ValidationSelection
        selections=[ValidationSelection("your-validation-set-id", 1), 
                    LabelingSelection(2)]
        ```

        This will require annotators to complete one validation task followed by two labeling tasks.
    """
    labeling = LabelingSelection
    validation = ValidationSelection
    conditional_validation = ConditionalValidationSelection
    demographic = DemographicSelection
    capped = CappedSelection
    shuffling = ShufflingSelection
