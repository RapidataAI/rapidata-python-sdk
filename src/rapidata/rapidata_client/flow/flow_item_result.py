from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlowItemResult:
    """Result of a flow item containing elo scores and vote count.

    Attributes:
        datapoints: Mapping of asset identifier to elo score.
        total_votes: Total number of votes cast for this flow item.
    """

    datapoints: dict[str, int]
    total_votes: int
