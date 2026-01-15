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
from rapidata.api_client.models.i_asset_input import IAssetInput


class MultiRankingWorkflow(Workflow):
    modality = RapidModality.COMPARE

    def __init__(
        self,
        instruction: str,
        comparison_budget_per_ranking: int,
        random_comparisons_ratio,
        elo_start: int = 1200,
        elo_k_factor: int = 40,
        elo_scaling_factor: int = 400,
        contexts: dict[str, str] | None = None,
        media_contexts: dict[str, IAssetInput] | None = None,
    ):
        from rapidata.api_client.models.i_pair_maker_config_model import (
            IPairMakerConfigModel,
        )
        from rapidata.api_client.models.i_pair_maker_config_model_online_pair_maker_config_model import (
            IPairMakerConfigModelOnlinePairMakerConfigModel,
        )
        from rapidata.api_client.models.elo_config_model import EloConfigModel

        super().__init__(type="CompareWorkflowConfig")

        self.contexts = contexts
        self.media_contexts = media_contexts

        self.instruction = instruction
        self.comparison_budget_per_ranking = comparison_budget_per_ranking
        self.random_comparisons_ratio = random_comparisons_ratio
        self.elo_start = elo_start
        self.elo_k_factor = elo_k_factor
        self.elo_scaling_factor = elo_scaling_factor

        self.pair_maker_config = IPairMakerConfigModel(
            actual_instance=IPairMakerConfigModelOnlinePairMakerConfigModel(
                _t="OnlinePairMaker",
                totalComparisonBudget=comparison_budget_per_ranking,
                randomMatchesRatio=random_comparisons_ratio,
            ),
        )

        self.elo_config = EloConfigModel(
            startingElo=elo_start,
            kFactor=elo_k_factor,
            scalingFactor=elo_scaling_factor,
        )

    def _to_model(self) -> IOrderWorkflowModel:
        return IOrderWorkflowModel(
            actual_instance=IOrderWorkflowModelGroupedRankingWorkflowModel(
                _t="GroupedRankingWorkflow",
                criteria=self.instruction,
                eloConfig=self.elo_config,
                pairMakerConfig=self.pair_maker_config,
                contexts=self.contexts,
                contextAssets=self.media_contexts,
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
        return f"MultiRankingWorkflow(instruction={self.instruction!r}, comparison_budget_per_ranking={self.comparison_budget_per_ranking!r}, random_comparisons_ratio={self.random_comparisons_ratio!r}, elo_start={self.elo_start!r}, elo_k_factor={self.elo_k_factor!r}, elo_scaling_factor={self.elo_scaling_factor!r})"
