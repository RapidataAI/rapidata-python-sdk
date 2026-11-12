from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.rapidata_client.referee._adaptive_stopping_referee import (
        AdaptiveStoppingReferee,
    )

# Mirrors the server default; requests leave the field out so the server stays the source of truth.
_DEFAULT_MAX_RESPONSES = 100


def _check_open_unit_interval(name: str, value: float | None) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number between 0 and 1 (exclusive).")
    if not 0 < value < 1:
        raise ValueError(f"{name} must be between 0 and 1 (exclusive), got {value}.")


@dataclass(frozen=True)
class AdaptiveStopping:
    """Stops collecting responses on a compare datapoint once the outcome is clear.

    Responses are collected until it is clear which option wins, until the two options
    are so close that the datapoint is called ambiguous, or until ``max_responses`` is
    reached. Clear pairs finish after a few responses; close pairs use more.

    It is the default for compare job definitions. Pass it as ``responses_per_datapoint``
    to change a parameter, or assign it to ``RapidataJobDefinition.responses_per_datapoint``
    to switch an existing compare definition. Other job types raise ``ValueError``.

    Leave a parameter as ``None`` to use its default. A saved job definition always
    carries the resolved values.

    Args:
        max_responses (int, optional): The most responses collected per datapoint.
            Default: 100. Cost and progress count this many responses per datapoint.
        min_confidence (float, optional): How certain the result must be before a
            winner is called, between 0 and 1 (exclusive). Default: 0.9.
        ambiguity_threshold (float, optional): How close the two options must be before
            the datapoint is called ambiguous, as a normalized Gini impurity between 0
            and 1 (exclusive). Higher is stricter: it needs a closer tie, so it costs
            more responses. Default: 0.64, which matches a 20%-80% split.

    Attributes:
        max_responses (int | None): The response cap, or None for the default.
        min_confidence (float | None): The confidence level, or None for the default.
        ambiguity_threshold (float | None): The ambiguity threshold, or None for the default.
    """

    max_responses: int | None = None
    min_confidence: float | None = None
    ambiguity_threshold: float | None = None

    def __post_init__(self) -> None:
        if self.max_responses is not None and (
            isinstance(self.max_responses, bool)
            or not isinstance(self.max_responses, int)
        ):
            raise ValueError("max_responses must be an integer.")
        if self.max_responses is not None and self.max_responses < 1:
            raise ValueError(
                f"max_responses must be greater than 0, got {self.max_responses}."
            )
        _check_open_unit_interval("min_confidence", self.min_confidence)
        _check_open_unit_interval("ambiguity_threshold", self.ambiguity_threshold)

    @property
    def _responses_per_datapoint(self) -> int:
        return (
            self.max_responses
            if self.max_responses is not None
            else _DEFAULT_MAX_RESPONSES
        )

    def _to_referee(self) -> AdaptiveStoppingReferee:
        from rapidata.rapidata_client.referee._adaptive_stopping_referee import (
            AdaptiveStoppingReferee,
        )

        return AdaptiveStoppingReferee(
            max_votes=self.max_responses,
            min_confidence=self.min_confidence,
            ambiguity_threshold=self.ambiguity_threshold,
        )
