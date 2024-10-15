from rapidata.api_client.models.capped_selection import (
    CappedSelection as CappedSelectionModel,
)
from rapidata.api_client.models.capped_selection_selections_inner import (
    CappedSelectionSelectionsInner,
)
from rapidata.rapidata_client.selection.base_selection import Selection
from typing import Sequence


class CappedSelection(Selection):

    def __init__(self, selections: Sequence[Selection], max_rapids: int):
        self.selections = selections
        self.max_rapids = max_rapids

    def to_model(self):
        return CappedSelectionModel(
            _t="CappedSelection",
            selections=[
                CappedSelectionSelectionsInner(selection.to_model())
                for selection in self.selections
            ],
            max_rapids=self.max_rapids,
        )
