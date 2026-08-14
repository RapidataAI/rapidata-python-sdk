from enum import Enum

from rapidata.api_client.models.vote_aggregation import (
    VoteAggregation as VoteAggregationModel,
)


class VoteAggregation(Enum):
    """VoteAggregation Enum

    How the individual annotator responses on a single matchup (one comparison of
    two models on one prompt) are aggregated into that matchup's result.

    Attributes:
        MAJORITY_VOTE (VoteAggregation): Collapses each matchup to a single win for
            the side the majority of responses picked, splitting ties 0.5/0.5.
        ALL_VOTES (VoteAggregation): Counts every individual response as its own
            matchup.
    """

    MAJORITY_VOTE = VoteAggregationModel.MAJORITYVOTE
    ALL_VOTES = VoteAggregationModel.ALLVOTES

    def _to_backend_model(self) -> VoteAggregationModel:
        return VoteAggregationModel(self.value)

    @classmethod
    def _from_backend_model(cls, model: VoteAggregationModel) -> "VoteAggregation":
        return cls(model)
