from typing import Any
from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.rapidata_client.selection.retrieval_modes import RetrievalMode
from rapidata.api_client.models.labeling_selection import (
    LabelingSelection as LabelingSelectionModel,
)


class LabelingSelection(RapidataSelection):
    """Labeling selection class.
    
    Decides how many actual datapoints you want to show per session.
    
    Args:
        amount (int): The amount of labeling rapids that will be shown per session.
        retrieval_mode (RetrievalMode): The retrieval mode to use. Defaults to "Random".
        max_iterations (int | None): The maximum number an annotator can see the same task. Defaults to None.
            This parameter is only taken into account when using "Shuffled" or "Sequential" retrieval modes.
    """

    def __init__(self, amount: int, retrieval_mode: RetrievalMode = RetrievalMode.Random, max_iterations: int | None = None):
        self.amount = amount
        self.retrieval_mode = retrieval_mode
        self.max_iterations = max_iterations

    def _to_model(self) -> Any:
        return LabelingSelectionModel(_t="LabelingSelection", amount=self.amount, retrievalMode=self.retrieval_mode.value, maxIterations=self.max_iterations)
