from rapidata.api_client import CompareWorkflowModelPairMakerConfig, OnlinePairMakerConfigModel, EloConfigModel
from rapidata.api_client.models.compare_workflow_model import CompareWorkflowModel
from rapidata.rapidata_client.workflow._base_workflow import Workflow

class RankingWorkflow(Workflow):


    def __init__(self,
                 criteria: str,
                 total_comparison_budget: int,
                 random_comparisons_ratio,
                 elo_start: int,
                 elo_k_factor: int,
                 elo_scaling_factor: int,
                 ):
        super().__init__(type="CompareWorkflowConfig")

        self.criteria = criteria
        self.pair_maker_config = CompareWorkflowModelPairMakerConfig(
            OnlinePairMakerConfigModel(
                _t='OnlinePairMaker',
                totalComparisonBudget=total_comparison_budget,
                randomMatchesRatio=random_comparisons_ratio,
            )
        )

        self.elo_config = EloConfigModel(
            startingElo=elo_start,
            kFactor=elo_k_factor,
            scalingFactor=elo_scaling_factor,
        )

    def _to_model(self) -> CompareWorkflowModel:

        return CompareWorkflowModel(
            _t="CompareWorkflow",
            criteria=self.criteria,
            eloConfig=self.elo_config,
            pairMakerConfig=self.pair_maker_config
        )
