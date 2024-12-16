
from rapidata.api_client.models.validation_selection import ValidationSelection as ValidationSelectionModel
from rapidata.rapidata_client.selection._base_selection import RapidataSelection


class ValidationSelection(RapidataSelection):
    """Validation selection class.

    Decides how many validation rapids you want to show per session.
    
    Args:
        validation_set_id (str): The id of the validation set to be used.
        amount (int): The amount of validation rapids that will be shown per session of this validation set.
    """

    def __init__(self, validation_set_id: str, amount: int = 1):
        self.validation_set_id = validation_set_id
        self.amount = amount

    def _to_model(self):
        return ValidationSelectionModel(_t="ValidationSelection", validationSetId=self.validation_set_id, amount=self.amount)
    