
from rapidata.api_client.models.validation_selection import ValidationSelection as ValidationSelectionModel
from rapidata.rapidata_client.selection.base_selection import Selection


class ValidationSelection(Selection):

    def __init__(self, validation_set_id: str, amount: int = 1):
        self.validation_set_id = validation_set_id
        self.amount = amount


    def to_model(self):
        return ValidationSelectionModel(_t="ValidationSelection", validationSetId=self.validation_set_id, amount=self.amount)
    