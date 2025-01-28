from rapidata.rapidata_client.selection import (
    DemographicSelection, 
    LabelingSelection, 
    ValidationSelection, 
    ConditionalValidationSelection, 
    CappedSelection)

class RapidataSelections:
    """RapidataSelections Classes

    Selections are used to define what type of tasks and in what order they are shown to the user. 
    All Tasks are called a "Session". A session can contain multiple tasks of different types.

    Example:
    ```python
        selections=[ValidationSelection("your-validation-set-id", 1), 
                    LabelingSelection(2)]
    ```

    The above example will create a session with a validation task followed by two labeling tasks.

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
