from typing import Any
from rapidata.rapidata_client.selection.base_selection import RapidataSelection
from rapidata.api_client.models.labeling_selection import (
    LabelingSelection as LabelingSelectionModel,
)


class LabelingSelection(RapidataSelection):

    def __init__(self, amount: int):
        self.amount = amount

    def to_model(self) -> Any:
        return LabelingSelectionModel(_t="LabelingSelection", amount=self.amount)
