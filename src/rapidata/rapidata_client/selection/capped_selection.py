from rapidata.api_client.models.capped_selection import (
    CappedSelection as CappedSelectionModel,
)
from rapidata.api_client.models.capped_selection_selections_inner import (
    CappedSelectionSelectionsInner,
)
from rapidata.rapidata_client.selection.base_selection import RapidataSelection
from typing import Sequence


class CappedSelection(RapidataSelection):
    """CappedSelection Class

    Takes in different selections and caps the amount of rapids that can be shown.
    
    Useful for demographic and conditional validation selections."""

    def __init__(self, selections: Sequence[RapidataSelection], max_rapids: int):
        """
        Initialize a CappedSelection instance.

        Args:
            selections (Sequence[RapidataSelection]): List of selections to cap.
            max_rapids (int): The maximum amount of rapids that can be shown for this selection.
        """
        self.selections = selections
        self.max_rapids = max_rapids

    def to_model(self):
        return CappedSelectionModel(
            _t="CappedSelection",
            selections=[
                CappedSelectionSelectionsInner(selection.to_model())
                for selection in self.selections
            ],
            maxRapids=self.max_rapids,
        )
