from typing import Literal


class DetailMapper:
    MIN_RESPONSES = 3

    @staticmethod
    def get_budget(level_of_detail: Literal["low", "medium", "high", "extreme"]) -> int:
        if level_of_detail == "low":
            return 2_000
        elif level_of_detail == "medium":
            return 4_000
        elif level_of_detail == "high":
            return 8_000
        elif level_of_detail == "extreme":
            return 16_000
        else:
            raise ValueError(
                "Invalid level of detail. Must be one of: 'low', 'medium', 'high', 'extreme'"
            )

    @staticmethod
    def get_level_of_detail(
        response_budget: int,
    ) -> Literal["low", "medium", "high", "extreme"]:
        if response_budget < 4_000:
            return "low"
        elif response_budget < 8_000:
            return "medium"
        elif response_budget < 16_000:
            return "high"
        return "extreme"
