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
    All selections combined are called a "Session". A session can contain multiple tasks of different types of tasks.
    As an example, a session might be 1 validation task, 2 labeling tasks.

    Attributes:
        labeling (LabelingSelection): Decides how many actual datapoints you want to show per session.
        validation (ValidationSelection): Decides how many validation rapids you want to show per session.
        conditional_validation (ConditionalValidationSelection): Probabilistically decides how many validation rapids you want to show per session based on the user score.
        demographic (DemographicSelection): Decides if and how many demographic questions you want to show per session.
        capped (CappedSelection): Takes in different selections and caps the amount of rapids that can be shown.
        shuffling (ShufflingSelection): Shuffles the selections provided in the list.
    
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
