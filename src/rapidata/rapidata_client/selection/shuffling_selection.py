
from rapidata.api_client.models.ab_test_selection_a_inner import AbTestSelectionAInner
from rapidata.api_client.models.shuffling_selection import ShufflingSelection as ShufflingSelectionModel
from rapidata.rapidata_client.selection._base_selection import RapidataSelection

from typing import Sequence


class ShufflingSelection(RapidataSelection):
    """ShufflingSelection Class

    Shuffles the selections provided in the list.
    
    Args:
        selections (Sequence[RapidataSelection]): List of selections to shuffle.

    Example:
        ```python
        selection = ShufflingSelection(
                    [ValidSelections("validation_id", 1), LabelingSelection(2)])
        ```
        This means that the users will get 1 validation task and 2 labeling tasks in a shuffled order.
    """

    def __init__(self, selections: Sequence[RapidataSelection]):
        self.selections = selections

    def _to_model(self) -> ShufflingSelectionModel:
        return ShufflingSelectionModel(
            _t="ShufflingSelection",
            selections=[
                AbTestSelectionAInner(selection._to_model())
                for selection in self.selections
            ]
        )
    