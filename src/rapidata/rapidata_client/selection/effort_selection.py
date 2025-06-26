from rapidata.rapidata_client.selection._base_selection import RapidataSelection
from rapidata.api_client.models.effort_capped_selection import EffortCappedSelection as EffortCappedSelectionModel
from rapidata.rapidata_client.selection.retrieval_modes import RetrievalMode


class EffortEstimationSelection(RapidataSelection):
    

    def __init__(self, effort_budget: int, retrieval_mode: RetrievalMode = RetrievalMode.Shuffled, max_iterations: int | None = None):
        self.effort_budget = effort_budget
        self.retrieval_mode = retrieval_mode
        self.max_iterations = max_iterations

    def _to_model(self):
        return EffortCappedSelectionModel(
            _t="EffortCappedSelection", 
            effortBudget=self.effort_budget, 
            retrievalMode=self.retrieval_mode.value, 
            maxIterations=self.max_iterations)
