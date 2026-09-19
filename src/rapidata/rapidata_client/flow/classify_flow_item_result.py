from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassifyDatapointResult:
    """Classification outcome of a single datapoint in a classify flow item.

    Attributes:
        majority_value: The category value chosen most often, or None on a tie.
        distribution: Mapping of category value to the number of responses that chose it.
        response_count: Number of responses collected for this datapoint.
    """

    majority_value: str | None
    distribution: dict[str, int]
    response_count: int


@dataclass(frozen=True)
class ClassifyFlowItemResult:
    """Result of a classify flow item.

    Attributes:
        datapoints: Mapping of asset identifier to its classification outcome.
        total_responses: Total number of responses collected for this flow item.
    """

    datapoints: dict[str, ClassifyDatapointResult]
    total_responses: int
