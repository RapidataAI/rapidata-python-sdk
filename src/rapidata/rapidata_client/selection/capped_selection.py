from rapidata.api_client.models.capped_selection import (
    CappedSelection as CappedSelectionModel,
)
from rapidata.api_client.models.capped_selection_selections_inner import (
    CappedSelectionSelectionsInner,
)
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from typing import Sequence


class CappedSelection(RapidataSelection):
    """CappedSelection Class

    Takes in different selections and caps the amount of rapids that can be shown.
    
    Useful for demographic and conditional validation selections.
    
    Args:
        selections (Sequence[RapidataSelection]): List of selections to cap.
        max_rapids (int): The maximum amount of rapids that can be shown for this selection.
    """

    def __init__(self, selections: Sequence[RapidataSelection], max_rapids: int):
        self.selections = selections
        self.max_rapids = max_rapids

    def _to_model(self):
        return CappedSelectionModel(
            _t="CappedSelection",
            selections=[
                CappedSelectionSelectionsInner(selection._to_model())
                for selection in self.selections
            ],
            maxRapids=self.max_rapids,
        )
