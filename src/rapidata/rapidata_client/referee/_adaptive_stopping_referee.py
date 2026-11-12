from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rapidata.rapidata_client.referee._base_referee import Referee

if TYPE_CHECKING:
    from rapidata.api_client.models.i_referee import IReferee

# Mirrors the backend default; requests leave maxVotes out so the backend stays the source of truth.
DEFAULT_ADAPTIVE_MAX_VOTES = 100


def _check_open_unit_interval(name: str, value: float | None) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number between 0 and 1 (exclusive).")
    if not 0 < value < 1:
        raise ValueError(f"{name} must be between 0 and 1 (exclusive), got {value}.")


class AdaptiveStoppingReferee(Referee):
    """Stops collecting votes on a compare datapoint once the outcome is clear.

    Votes are collected until it is clear which option wins, until the two options
    are so close that the datapoint is called ambiguous, or until ``max_votes`` is
    reached. Clear pairs finish after a few votes; close pairs use more.

    It is the default for compare job definitions. Pass it as ``responses_per_datapoint``
    to change a parameter, or assign it to ``RapidataJobDefinition.responses_per_datapoint``
    to switch an existing compare definition. Other job types raise ``ValueError``.

    Leave a parameter as ``None`` to use its default. A saved job definition always
    carries the resolved values.

    Args:
        max_votes (int, optional): The most votes collected per datapoint.
            Default: 100. Cost and progress count this many votes per datapoint.
        min_confidence (float, optional): How certain the result must be before a
            winner is called, between 0 and 1 (exclusive). Default: 0.9.
        ambiguity_threshold (float, optional): How close the two options must be before
            the datapoint is called ambiguous, as a normalized Gini impurity between 0
            and 1 (exclusive). Higher is stricter: it needs a closer tie, so it costs
            more votes. Default: 0.64, which matches a 20%-80% vote split.

    Attributes:
        max_votes (int | None): The vote cap, or None for the default.
        min_confidence (float | None): The confidence level, or None for the default.
        ambiguity_threshold (float | None): The ambiguity threshold, or None for the default.
    """

    def __init__(
        self,
        max_votes: int | None = None,
        min_confidence: float | None = None,
        ambiguity_threshold: float | None = None,
    ):
        if max_votes is not None and (
            isinstance(max_votes, bool) or not isinstance(max_votes, int)
        ):
            raise ValueError("max_votes must be an integer.")
        if max_votes is not None and max_votes < 1:
            raise ValueError(f"max_votes must be greater than 0, got {max_votes}.")
        _check_open_unit_interval("min_confidence", min_confidence)
        _check_open_unit_interval("ambiguity_threshold", ambiguity_threshold)

        super().__init__()
        self.max_votes = max_votes
        self.min_confidence = min_confidence
        self.ambiguity_threshold = ambiguity_threshold

    @property
    def _responses_per_datapoint(self) -> int:
        return (
            self.max_votes if self.max_votes is not None else DEFAULT_ADAPTIVE_MAX_VOTES
        )

    def _set_fields(self) -> dict[str, Any]:
        fields: dict[str, int | float | None] = {
            "maxVotes": self.max_votes,
            "minConfidence": self.min_confidence,
            "ambiguityThreshold": self.ambiguity_threshold,
        }
        return {key: value for key, value in fields.items() if value is not None}

    def _to_dict(self):
        return {"_t": "AdaptiveStoppingRefereeConfig", **self._set_fields()}

    def _to_model(self) -> IReferee:
        from rapidata.api_client.models.i_referee_adaptive_stopping_referee import (
            IRefereeAdaptiveStoppingReferee,
        )
        from rapidata.api_client.models.i_referee import IReferee

        return IReferee(
            actual_instance=IRefereeAdaptiveStoppingReferee(
                _t="AdaptiveStoppingReferee", **self._set_fields()
            )
        )

    def __str__(self) -> str:
        return (
            f"AdaptiveStoppingReferee(max_votes={self.max_votes}, "
            f"min_confidence={self.min_confidence}, "
            f"ambiguity_threshold={self.ambiguity_threshold})"
        )

    def __repr__(self) -> str:
        return self.__str__()
