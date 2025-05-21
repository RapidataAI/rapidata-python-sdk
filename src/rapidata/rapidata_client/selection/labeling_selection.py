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
        retrieval_mode (RetrievalMode): The retrieval mode to use. Defaults to "Shuffled".
        max_iterations (int | None): An annotator can answer the same task only once if the retrieval_mode is "Shuffled" 
            or "Sequential". max_iterations can increase the amount of responses an annotator can do 
            to the same task (datapoint).
    """

    def __init__(self, amount: int, retrieval_mode: RetrievalMode = RetrievalMode.Shuffled, max_iterations: int | None = None):
        self.amount = amount
        self.retrieval_mode = retrieval_mode
        self.max_iterations = max_iterations

    def _to_model(self) -> Any:
        return LabelingSelectionModel(_t="LabelingSelection", amount=self.amount, retrievalMode=self.retrieval_mode.value, maxIterations=self.max_iterations)
