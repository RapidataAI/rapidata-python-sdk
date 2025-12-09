from __future__ import annotations

from rapidata.rapidata_client.referee._base_referee import Referee
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.i_referee_model import IRefereeModel


class NaiveReferee(Referee):
    """A simple referee that completes a task after a fixed number of responses.

    This referee implements a straightforward approach to task completion,
    where the task is considered finished after a predetermined number of
    responses have been made, regardless of the content or quality of those responses.

    Args:
        responses (int, optional): The number of responses required
            to complete the task. Defaults to 10. This is per media item.

    Attributes:
        responses (int): The number of responses required to complete the task.
    """

    def __init__(self, responses: int = 10):
        if responses < 1:
            raise ValueError("The number of responses must be greater than 0.")
        super().__init__()
        self.responses = responses

    def _to_dict(self):
        return {
            "_t": "NaiveRefereeConfig",
            "guessesRequired": self.responses,
        }

    def _to_model(self) -> IRefereeModel:
        from rapidata.api_client.models.i_referee_model_naive_referee_model import (
            IRefereeModelNaiveRefereeModel,
        )
        from rapidata.api_client.models.i_referee_model import IRefereeModel

        return IRefereeModel(
            actual_instance=IRefereeModelNaiveRefereeModel(
                _t="NaiveReferee",
                totalVotes=self.responses,
            )
        )

    def __str__(self) -> str:
        return f"NaiveReferee(responses={self.responses})"

    def __repr__(self) -> str:
        return self.__str__()
