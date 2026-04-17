from __future__ import annotations

from rapidata.rapidata_client.referee._base_referee import Referee
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.i_referee_model import IRefereeModel


class BudgetReferee(Referee):
    """A referee that completes a ranking task after a fixed total budget of comparisons.

    This referee is used with FullPermutationPairMaker for ranking tasks, where
    the total number of comparisons across all pairs is budgeted rather than
    counted per individual item.

    Args:
        budget (int): The total number of comparisons to collect.
    """

    def __init__(self, budget: int):
        if budget < 1:
            raise ValueError("The budget must be greater than 0.")
        super().__init__()
        self.budget = budget

    def _to_dict(self):
        return {
            "_t": "BudgetReferee",
            "totalBudget": self.budget,
        }

    def _to_model(self) -> IRefereeModel:
        from rapidata.api_client.models.i_referee_model_budget_referee_model import (
            IRefereeModelBudgetRefereeModel,
        )
        from rapidata.api_client.models.i_referee_model import IRefereeModel

        return IRefereeModel(
            actual_instance=IRefereeModelBudgetRefereeModel(
                _t="BudgetReferee",
                totalBudget=self.budget,
            )
        )

    def __str__(self) -> str:
        return f"BudgetReferee(budget={self.budget})"

    def __repr__(self) -> str:
        return self.__str__()
