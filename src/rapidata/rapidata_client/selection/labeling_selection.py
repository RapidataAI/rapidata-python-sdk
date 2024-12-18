from typing import Any
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.api_client.models.labeling_selection import (
    LabelingSelection as LabelingSelectionModel,
)


class LabelingSelection(RapidataSelection):
    """Labeling selection class.
    
    Decides how many actual datapoints you want to show per session.
    
    Args:
        amount (int): The amount of labeling rapids that will be shown per session.
    """

    def __init__(self, amount: int):
        self.amount = amount

    def _to_model(self) -> Any:
        return LabelingSelectionModel(_t="LabelingSelection", amount=self.amount)
