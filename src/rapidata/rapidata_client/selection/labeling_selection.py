from __future__ import annotations

from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.rapidata_client.selection.rapidata_retrieval_modes import (
    RapidataRetrievalMode,
)


class LabelingSelection(RapidataSelection):
    """Labeling selection class.

    Decides how many actual datapoints you want to show per session.

    Args:
        amount (int): The amount of labeling rapids that will be shown per session.
        retrieval_mode (RetrievalMode): The retrieval mode to use. Defaults to "Shuffled".
        max_iterations (int | None): An annotator can answer the same task only once if the retrieval_mode is "Shuffled"
            or "Sequential". max_iterations can increase the amount of responses an annotator can do
            to the same task (datapoint).
        advance_on_view (bool): Move an annotator past a task as soon as it is shown, even without an answer,
            so a skipped task is not served to them again. Requires "Shuffled" or "Sequential". Defaults to False.
    """

    def __init__(
        self,
        amount: int,
        retrieval_mode: RapidataRetrievalMode = RapidataRetrievalMode.Shuffled,
        max_iterations: int | None = None,
        advance_on_view: bool = False,
    ):
        if advance_on_view and retrieval_mode == RapidataRetrievalMode.Random:
            raise ValueError(
                'advance_on_view requires the "Shuffled" or "Sequential" retrieval mode'
            )
        self.amount = amount
        self.retrieval_mode = retrieval_mode
        self.max_iterations = max_iterations
        self.advance_on_view = advance_on_view

    def _to_model(self):
        from rapidata.api_client.models.i_selection import ISelection
        from rapidata.api_client.models.i_selection_labeling_selection import (
            ISelectionLabelingSelection,
        )

        return ISelection(
            actual_instance=ISelectionLabelingSelection(
                _t="LabelingSelection",
                amount=self.amount,
                retrievalMode=self.retrieval_mode.value,
                maxIterations=self.max_iterations,
                advanceOnView=self.advance_on_view,
            )
        )

    def __str__(self) -> str:
        return f"LabelingSelection(amount={self.amount}, retrieval_mode={self.retrieval_mode}, max_iterations={self.max_iterations}, advance_on_view={self.advance_on_view})"

    def __repr__(self) -> str:
        return self.__str__()
