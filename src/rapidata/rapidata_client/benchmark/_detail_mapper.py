from typing import Literal

LevelOfDetail = Literal["debug", "low", "medium", "high", "very high"]

# What `level_of_detail` reports back: a named level, or "custom" for any budget
# that doesn't line up with one of the named levels (e.g. a raw int budget).
ResolvedLevelOfDetail = Literal["debug", "low", "medium", "high", "very high", "custom"]

_LEVEL_BUDGETS: dict[str, int] = {
    "debug": 20,
    "low": 2_000,
    "medium": 4_000,
    "high": 8_000,
    "very high": 16_000,
}


class DetailMapper:
    @staticmethod
    def get_budget(level_of_detail: LevelOfDetail) -> int:
        try:
            return _LEVEL_BUDGETS[level_of_detail]
        except KeyError:
            raise ValueError(
                "Invalid level of detail. Must be one of: "
                + ", ".join(LevelOfDetail.__args__)
                + " (or pass an integer response budget for a custom level)"
            )

    @staticmethod
    def resolve_budget(level_of_detail: "LevelOfDetail | int") -> int:
        """Turns a named level or a raw response budget into a concrete budget."""
        # bool is an int subclass — reject it so `True` isn't read as a budget of 1.
        if isinstance(level_of_detail, bool) or not isinstance(
            level_of_detail, (int, str)
        ):
            raise ValueError(
                "Level of detail must be one of "
                + ", ".join(LevelOfDetail.__args__)
                + " or a positive integer response budget"
            )

        if isinstance(level_of_detail, int):
            if level_of_detail < 1:
                raise ValueError("Response budget must be a positive integer")
            return level_of_detail

        return DetailMapper.get_budget(level_of_detail)

    @staticmethod
    def get_level_of_detail(response_budget: int) -> ResolvedLevelOfDetail:
        for level, budget in _LEVEL_BUDGETS.items():
            if budget == response_budget:
                return level  # type: ignore[return-value]
        return "custom"
