from typing import Literal

LevelOfDetail = Literal["debug", "low", "medium", "high", "very high"]


class DetailMapper:
    @staticmethod
    def get_budget(level_of_detail: LevelOfDetail) -> int:
        if level_of_detail == "debug":
            return 20
        elif level_of_detail == "low":
            return 2_000
        elif level_of_detail == "medium":
            return 4_000
        elif level_of_detail == "high":
            return 8_000
        elif level_of_detail == "very high":
            return 16_000
        else:
            raise ValueError(
                "Invalid level of detail. Must be one of: 'debug', 'low', 'medium', 'high', 'very high'"
            )

    @staticmethod
    def get_level_of_detail(response_budget: int) -> LevelOfDetail:
        if response_budget <= 20:
            return "debug"
        elif response_budget < 4_000:
            return "low"
        elif response_budget < 8_000:
            return "medium"
        elif response_budget < 16_000:
            return "high"
        return "very high"
