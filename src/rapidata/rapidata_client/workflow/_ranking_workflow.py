from rapidata.api_client import CompareWorkflowModelPairMakerConfig, OnlinePairMakerConfigModel, EloConfigModel
from rapidata.api_client.models.compare_workflow_model import CompareWorkflowModel
from rapidata.rapidata_client.workflow._base_workflow import Workflow

class RankingWorkflow(Workflow):


    def __init__(self,
                 criteria: str,
                 total_comparison_budget: int,
                 random_comparisons_ratio,
                 starting_elo: int,
                 k_factor: int,
                 scaling_factor: int,
                 ):
        super().__init__(type="CompareWorkflowConfig")
        assert total_comparison_budget > 0, 'The comparison budget must be positive'
        assert 0 <= random_comparisons_ratio <= 1, 'The ratio of randomly arranged matches should be between 0 and 1 (inclusive)'

        self.criteria = criteria
        self.pair_maker_config = CompareWorkflowModelPairMakerConfig(
            OnlinePairMakerConfigModel(
                _t='OnlinePairMaker',
                totalComparisonBudget=total_comparison_budget,
                randomMatchesRatio=random_comparisons_ratio,
            )
        )

        self.elo_settings = dict(
            startingElo=starting_elo,
            kFactor=k_factor,
            scalingFactor=scaling_factor,
        )

    def _to_model(self) -> CompareWorkflowModel:

        return CompareWorkflowModel(
            _t="CompareWorkflow",
            criteria=self.criteria,
            eloConfig=EloConfigModel(**self.elo_settings),
            pairMakerConfig=self.pair_maker_config
        )
