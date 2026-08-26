from rapidata.api_client.models.add_validation_rapid_model import IRapidPayload
from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.api_client.models.i_order_workflow_input_grouped_ranking_workflow_input import (
    IOrderWorkflowInputGroupedRankingWorkflowInput,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_compare_payload import (
    IRapidPayloadComparePayload,
)
from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality

FULL_PERMUTATION_GROUP_SIZE_THRESHOLD = 10
BRADLEY_TERRY_DEFAULT_STARTING_SCORE = 1200


class MultiRankingWorkflow(Workflow):
    modality = RapidModality.COMPARE
    task_type = "Ranking"

    def __init__(
        self,
        instruction: str,
        comparison_budget_per_ranking: int,
        random_comparisons_ratio: float,
        max_group_size: int,
        responses_per_comparison: int,
    ):
        from rapidata.api_client.models.i_pair_maker_config import (
            IPairMakerConfig,
        )
        from rapidata.api_client.models.i_pair_maker_config_online_pair_maker_config import (
            IPairMakerConfigOnlinePairMakerConfig,
        )
        from rapidata.api_client.models.i_pair_maker_config_full_permutation_pair_maker_config import (
            IPairMakerConfigFullPermutationPairMakerConfig,
        )
        from rapidata.api_client.models.i_ranking_config import (
            IRankingConfig,
        )
        from rapidata.api_client.models.i_ranking_config_bradley_terry_ranking_config import (
            IRankingConfigBradleyTerryRankingConfig,
        )

        super().__init__(type="CompareWorkflowConfig")

        self._validate_instruction(instruction)
        self.instruction = instruction
        self.comparison_budget_per_ranking = comparison_budget_per_ranking
        self.random_comparisons_ratio = random_comparisons_ratio
        self.max_group_size = max_group_size
        self.responses_per_comparison = responses_per_comparison

        if max_group_size <= FULL_PERMUTATION_GROUP_SIZE_THRESHOLD:
            self.pair_maker_config = IPairMakerConfig(
                actual_instance=IPairMakerConfigFullPermutationPairMakerConfig(
                    _t="FullPermutationPairMaker",
                ),
            )
            # The full-permutation pair maker takes no budget: it emits each
            # unique pair exactly once. Spread the budget over the pairs via
            # the per-rapid response requirement so the total still honors it.
            pairs = max_group_size * (max_group_size - 1) // 2
            comparisons_per_pair = comparison_budget_per_ranking // pairs
            if comparisons_per_pair < 1:
                logger.warning(
                    "comparison_budget_per_ranking=%d is below the %d unique pairs "
                    "of a %d-item ranking; every pair is compared at least once, "
                    "so the budget will be exceeded.",
                    comparison_budget_per_ranking,
                    pairs,
                    max_group_size,
                )
                comparisons_per_pair = 1
            self.responses_per_datapoint = (
                comparisons_per_pair * responses_per_comparison
            )
        else:
            self.pair_maker_config = IPairMakerConfig(
                actual_instance=IPairMakerConfigOnlinePairMakerConfig(
                    _t="OnlinePairMaker",
                    totalComparisonBudget=comparison_budget_per_ranking,
                    randomMatchesRatio=random_comparisons_ratio,
                ),
            )
            self.responses_per_datapoint = responses_per_comparison

        self.ranking_config = IRankingConfig(
            actual_instance=IRankingConfigBradleyTerryRankingConfig(
                _t="BradleyTerryRankingConfig",
                startingScore=BRADLEY_TERRY_DEFAULT_STARTING_SCORE,
            ),
        )

    def _to_model(self) -> IOrderWorkflowInput:
        return IOrderWorkflowInput(
            actual_instance=IOrderWorkflowInputGroupedRankingWorkflowInput(
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
        return f"MultiRankingWorkflow(instruction={self.instruction!r}, comparison_budget_per_ranking={self.comparison_budget_per_ranking!r}, random_comparisons_ratio={self.random_comparisons_ratio!r}, max_group_size={self.max_group_size!r}, responses_per_comparison={self.responses_per_comparison!r})"
