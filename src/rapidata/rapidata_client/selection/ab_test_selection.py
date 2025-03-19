from rapidata.api_client.models.ab_test_selection import (
    AbTestSelection as AbTestSelectionModel,
)
from rapidata.api_client.models.ab_test_selection_a_inner import (
    AbTestSelectionAInner,
)
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from typing import Sequence


class AbTestSelection(RapidataSelection):
    """AbTestSelection Class
    
    Splits the userbase into two segments and serves them a different collection of rapids.

    Useful for A/B Test.
    
    Args:
        a_selections (Sequence[RapidataSelection]): List of selections for group A.
        b_selections (Sequence[RapidataSelection]): List of selections for group B.
    """

    def __init__(self, a_selections: Sequence[RapidataSelection], b_selections: Sequence[RapidataSelection]):
        self.a_selections = a_selections
        self.b_selections = b_selections

    def _to_model(self):
        return AbTestSelectionModel(
            _t="AbTestSelection",
            a=[
                AbTestSelectionAInner(selection._to_model())
                for selection in self.a_selections
            ],
            b=[
                AbTestSelectionAInner(selection._to_model())
                for selection in self.b_selections
            ],
        )
