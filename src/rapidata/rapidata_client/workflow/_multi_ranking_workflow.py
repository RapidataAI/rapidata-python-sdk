from rapidata.api_client.models.add_validation_rapid_model import IRapidPayload
from rapidata.api_client.models.i_order_workflow_model import IOrderWorkflowModel
from rapidata.api_client.models.i_order_workflow_model_grouped_ranking_workflow_model import (
    IOrderWorkflowModelGroupedRankingWorkflowModel,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_compare_payload import (
    IRapidPayloadComparePayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality

FULL_PERMUTATION_GROUP_SIZE_THRESHOLD = 10


class MultiRankingWorkflow(Workflow):
    modality = RapidModality.COMPARE

    def __init__(
        self,
        instruction: str,
        comparison_budget_per_ranking: int,
        random_comparisons_ratio: float,
        group_sizes: list[int],
    ):
        from rapidata.api_client.models.i_pair_maker_config_model import (
            IPairMakerConfigModel,
        )
        from rapidata.api_client.models.i_pair_maker_config_model_online_pair_maker_config_model import (
            IPairMakerConfigModelOnlinePairMakerConfigModel,
        )
        from rapidata.api_client.models.i_pair_maker_config_model_full_permutation_pair_maker_config_model import (
            IPairMakerConfigModelFullPermutationPairMakerConfigModel,
        )
        from rapidata.api_client.models.i_ranking_config_model import (
            IRankingConfigModel,
        )
        from rapidata.api_client.models.i_ranking_config_model_bradley_terry_ranking_config_model import (
            IRankingConfigModelBradleyTerryRankingConfigModel,
        )

        super().__init__(type="CompareWorkflowConfig")

        self.instruction = instruction
        self.comparison_budget_per_ranking = comparison_budget_per_ranking
        self.random_comparisons_ratio = random_comparisons_ratio
        self.group_sizes = group_sizes
        self.uses_full_permutation = bool(
            group_sizes
            and all(size <= FULL_PERMUTATION_GROUP_SIZE_THRESHOLD for size in group_sizes)
        )

        if self.uses_full_permutation:
            self.pair_maker_config = IPairMakerConfigModel(
                actual_instance=IPairMakerConfigModelFullPermutationPairMakerConfigModel(
                    _t="FullPermutationPairMaker",
                ),
            )
        else:
            self.pair_maker_config = IPairMakerConfigModel(
                actual_instance=IPairMakerConfigModelOnlinePairMakerConfigModel(
                    _t="OnlinePairMaker",
                    totalComparisonBudget=comparison_budget_per_ranking,
                    randomMatchesRatio=random_comparisons_ratio,
                ),
            )

        self.ranking_config = IRankingConfigModel(
            actual_instance=IRankingConfigModelBradleyTerryRankingConfigModel(
                _t="BradleyTerryRankingConfig",
            ),
        )

    def _to_model(self) -> IOrderWorkflowModel:
        return IOrderWorkflowModel(
            actual_instance=IOrderWorkflowModelGroupedRankingWorkflowModel(
                _t="GroupedRankingWorkflow",
                criteria=self.instruction,
                pairMakerConfig=self.pair_maker_config,
                rankingConfig=self.ranking_config,
            )
        )

    def _get_instruction(self) -> str:
        return self.instruction

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        return IRapidPayload(
            actual_instance=IRapidPayloadComparePayload(
                _t="ComparePayload",
                criteria=self.instruction,
            )
        )

    def __str__(self) -> str:
        return f"MultiRankingWorkflow(instruction='{self.instruction}')"

    def __repr__(self) -> str:
        return f"MultiRankingWorkflow(instruction={self.instruction!r}, comparison_budget_per_ranking={self.comparison_budget_per_ranking!r}, random_comparisons_ratio={self.random_comparisons_ratio!r}, group_sizes={self.group_sizes!r})"
