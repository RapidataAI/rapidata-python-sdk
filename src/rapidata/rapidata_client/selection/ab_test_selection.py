from __future__ import annotations

from typing import Sequence

from rapidata.rapidata_client.selection._base_selection import RapidataSelection


class AbTestSelection(RapidataSelection):
    """AbTestSelection Class

    Splits the userbase into two segments and serves them a different collection of rapids.

    Useful for A/B Test.

    Args:
        a_selections (Sequence[RapidataSelection]): List of selections for group A.
        b_selections (Sequence[RapidataSelection]): List of selections for group B.
    """

    def __init__(
        self,
        a_selections: Sequence[RapidataSelection],
        b_selections: Sequence[RapidataSelection],
    ):
        self.a_selections = a_selections
        self.b_selections = b_selections

    def _to_model(self):
        from rapidata.api_client.models.i_selection import ISelection
        from rapidata.api_client.models.i_selection_ab_test_selection import (
            ISelectionAbTestSelection,
        )

        return ISelection(
            actual_instance=ISelectionAbTestSelection(
                _t="AbTestSelection",
                a=[selection._to_model() for selection in self.a_selections],
                b=[selection._to_model() for selection in self.b_selections],
            )
        )

    def __str__(self) -> str:
        return f"AbTestSelection(a_selections={self.a_selections}, b_selections={self.b_selections})"

    def __repr__(self) -> str:
        return self.__str__()
