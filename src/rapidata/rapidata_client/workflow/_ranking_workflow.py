from rapidata.api_client import (
    CompareWorkflowModelPairMakerConfig,
    OnlinePairMakerConfigModel,
    EloConfigModel,
)
from rapidata.api_client.models.compare_workflow_model import CompareWorkflowModel
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client import ComparePayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.rapidata_client.datapoints.metadata import (
    MediaAssetMetadata,
    PromptMetadata,
)
from rapidata.api_client.models.compare_workflow_model_metadata_inner import (
    CompareWorkflowModelMetadataInner,
)
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
import itertools
import random
from typing import cast


class RankingWorkflow(Workflow):
    modality = RapidModality.COMPARE

    def __init__(
        self,
        instruction: str,
        total_comparison_budget: int,
        random_comparisons_ratio,
        elo_start: int = 1200,
        elo_k_factor: int = 40,
        elo_scaling_factor: int = 400,
        media_context: str | None = None,
        context: str | None = None,
        file_uploader: AssetUploader | None = None,
    ):
        super().__init__(type="CompareWorkflowConfig")

        self.media_context = media_context
        self.context = context

        self.metadatas = []
        if media_context:
            assert (
                file_uploader is not None
            ), "File uploader is required if media_context is provided"
            self.metadatas.append(
                MediaAssetMetadata(
                    internal_file_name=file_uploader.upload_asset(media_context)
                )
            )
        if context:
            self.metadatas.append(PromptMetadata(prompt=context))

        self.instruction = instruction
        self.total_comparison_budget = total_comparison_budget
        self.random_comparisons_ratio = random_comparisons_ratio
        self.elo_start = elo_start
        self.elo_k_factor = elo_k_factor
        self.elo_scaling_factor = elo_scaling_factor

        self.pair_maker_config = CompareWorkflowModelPairMakerConfig(
            OnlinePairMakerConfigModel(
                _t="OnlinePairMaker",
                totalComparisonBudget=total_comparison_budget,
                randomMatchesRatio=random_comparisons_ratio,
            )
        )

        self.elo_config = EloConfigModel(
            startingElo=elo_start,
            kFactor=elo_k_factor,
            scalingFactor=elo_scaling_factor,
        )

    def _get_instruction(self) -> str:
        return self.instruction

    def _to_model(self) -> CompareWorkflowModel:

        return CompareWorkflowModel(
            _t="CompareWorkflow",
            criteria=self.instruction,
            eloConfig=self.elo_config,
            pairMakerConfig=self.pair_maker_config,
            metadata=[
                CompareWorkflowModelMetadataInner(metadata.to_model())
                for metadata in self.metadatas
            ],
        )

    def _to_payload(self, datapoint: Datapoint) -> ComparePayload:
        return ComparePayload(
            _t="ComparePayload",
            criteria=self.instruction,
        )

    def _format_datapoints(self, datapoints: list[Datapoint]) -> list[Datapoint]:
        if len(datapoints) < 3:
            raise ValueError("RankingWorkflow requires at least three datapoints")
        desired_length = len(datapoints)
        assets = [datapoint.asset for datapoint in datapoints]
        pairs = list(map(list, itertools.combinations(assets, 2)))
        sampled_pairs = random.sample(pairs, desired_length)
        formatted_datapoints = [
            Datapoint(
                asset=cast(list[str], pair),
                data_type=datapoints[0].data_type,
                context=self.context,
                media_context=self.media_context,
            )
            for pair in sampled_pairs
        ]
        return formatted_datapoints

    def __str__(self) -> str:
        return f"RankingWorkflow(instruction='{self.instruction}', metadatas={self.metadatas})"

    def __repr__(self) -> str:
        return f"RankingWorkflow(instruction={self.instruction!r}, total_comparison_budget={self.total_comparison_budget!r}, random_comparisons_ratio={self.random_comparisons_ratio!r}, elo_start={self.elo_start!r}, elo_k_factor={self.elo_k_factor!r}, elo_scaling_factor={self.elo_scaling_factor!r}, metadatas={self.metadatas!r})"
