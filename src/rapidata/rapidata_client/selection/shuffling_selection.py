from __future__ import annotations

from typing import Sequence

from rapidata.rapidata_client.selection._base_selection import RapidataSelection


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

    def _to_model(self):
        from rapidata.api_client.models.i_selection import ISelection
        from rapidata.api_client.models.i_selection_shuffling_selection import (
            ISelectionShufflingSelection,
        )

        return ISelection(
            actual_instance=ISelectionShufflingSelection(
                _t="ShufflingSelection",
                selections=[selection._to_model() for selection in self.selections],
            )
        )

    def __str__(self) -> str:
        return f"ShufflingSelection(selections={self.selections})"

    def __repr__(self) -> str:
        return self.__str__()
