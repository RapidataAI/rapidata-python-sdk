from __future__ import annotations

from typing import Sequence

from rapidata.rapidata_client.selection._base_selection import RapidataSelection


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
        from rapidata.api_client.models.i_selection import ISelection
        from rapidata.api_client.models.i_selection_capped_selection import (
            ISelectionCappedSelection,
        )

        return ISelection(
            actual_instance=ISelectionCappedSelection(
                _t="CappedSelection",
                selections=[selection._to_model() for selection in self.selections],
                maxRapids=self.max_rapids,
            )
        )

    def __str__(self) -> str:
        return f"CappedSelection(selections={self.selections}, max_rapids={self.max_rapids})"

    def __repr__(self) -> str:
        return self.__str__()
