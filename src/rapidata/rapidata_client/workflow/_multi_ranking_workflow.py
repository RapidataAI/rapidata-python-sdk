from rapidata.api_client import (
    CompareWorkflowModelPairMakerConfig,
    OnlinePairMakerConfigModel,
    EloConfigModel,
)
from rapidata.api_client.models.grouped_ranking_workflow_model import (
    GroupedRankingWorkflowModel,
)
from rapidata.api_client.models.create_datapoint_from_files_model_metadata_inner import (
    CreateDatapointFromFilesModelMetadataInner,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client import ComparePayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.rapidata_client.datapoints.metadata import Metadata
from rapidata.api_client.models.grouped_ranking_workflow_model import (
    GroupedRankingWorkflowModel,
)


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
        metadatas: list[Metadata] = [],
    ):
        super().__init__(type="CompareWorkflowConfig")

        self.metadatas = metadatas

        self.instruction = instruction
        self.comparison_budget_per_ranking = comparison_budget_per_ranking
        self.random_comparisons_ratio = random_comparisons_ratio
        self.elo_start = elo_start
        self.elo_k_factor = elo_k_factor
        self.elo_scaling_factor = elo_scaling_factor

        self.pair_maker_config = CompareWorkflowModelPairMakerConfig(
            OnlinePairMakerConfigModel(
                _t="OnlinePairMaker",
                totalComparisonBudget=comparison_budget_per_ranking,
                randomMatchesRatio=random_comparisons_ratio,
            )
        )

        self.elo_config = EloConfigModel(
            startingElo=elo_start,
            kFactor=elo_k_factor,
            scalingFactor=elo_scaling_factor,
        )

    def _to_model(self) -> GroupedRankingWorkflowModel:

        return GroupedRankingWorkflowModel(
            _t="GroupedRankingWorkflow",
            criteria=self.instruction,
            eloConfig=self.elo_config,
            pairMakerConfig=self.pair_maker_config,
            metadata=[
                CreateDatapointFromFilesModelMetadataInner(metadata.to_model())
                for metadata in self.metadatas
            ],
        )

    def _to_payload(self, datapoint: Datapoint) -> ComparePayload:
        return ComparePayload(
            _t="ComparePayload",
            criteria=self.instruction,
        )

    def __str__(self) -> str:
        return f"RankingWorkflow(instruction='{self.instruction}', metadatas={self.metadatas})"

    def __repr__(self) -> str:
        return f"RankingWorkflow(instruction={self.instruction!r}, comparison_budget_per_ranking={self.comparison_budget_per_ranking!r}, random_comparisons_ratio={self.random_comparisons_ratio!r}, elo_start={self.elo_start!r}, elo_k_factor={self.elo_k_factor!r}, elo_scaling_factor={self.elo_scaling_factor!r}, metadatas={self.metadatas!r})"
