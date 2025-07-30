import pandas as pd
from typing import Literal, Optional

from rapidata.rapidata_client.logging import logger
from rapidata.rapidata_client.benchmark._detail_mapper import DetailMapper
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.update_leaderboard_response_config_model import (
    UpdateLeaderboardResponseConfigModel,
)


class RapidataLeaderboard:
    """
    An instance of a Rapidata leaderboard.

    Used to interact with a specific leaderboard in the Rapidata system, such as retrieving prompts and evaluating models.

    Args:
        name: The name that will be used to identify the leaderboard on the overview.
        instruction: The instruction that will determine what how the models will be evaluated.
        show_prompt: Whether to show the prompt to the users.
        id: The ID of the leaderboard.
        openapi_service: The OpenAPIService instance for API interaction.
    """

    def __init__(
        self,
        name: str,
        instruction: str,
        show_prompt: bool,
        show_prompt_asset: bool,
        inverse_ranking: bool,
        response_budget: int,
        min_responses_per_matchup: int,
        id: str,
        openapi_service: OpenAPIService,
    ):
        self.__openapi_service = openapi_service
        self.__name = name
        self.__instruction = instruction
        self.__show_prompt = show_prompt
        self.__show_prompt_asset = show_prompt_asset
        self.__inverse_ranking = inverse_ranking
        self.__response_budget = response_budget
        self.__min_responses_per_matchup = min_responses_per_matchup
        self.id = id

    @property
    def level_of_detail(self) -> Literal["low", "medium", "high", "very high"]:
        """
        Returns the level of detail of the leaderboard.
        """
        return DetailMapper.get_level_of_detail(self.__response_budget)

    @level_of_detail.setter
    def level_of_detail(
        self, level_of_detail: Literal["low", "medium", "high", "very high"]
    ):
        """
        Sets the level of detail of the leaderboard.
        """
        logger.debug(f"Setting level of detail to {level_of_detail}")
        self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_response_config_put(
            leaderboard_id=self.id,
            update_leaderboard_response_config_model=UpdateLeaderboardResponseConfigModel(
                responseBudget=DetailMapper.get_budget(level_of_detail),
                minResponses=self.__min_responses_per_matchup,
            ),
        )
        self.__response_budget = DetailMapper.get_budget(level_of_detail)

    @property
    def min_responses_per_matchup(self) -> int:
        """
        Returns the minimum number of responses required to be considered for the leaderboard.
        """
        return self.__min_responses_per_matchup

    @min_responses_per_matchup.setter
    def min_responses_per_matchup(self, min_responses: int):
        """
        Sets the minimum number of responses required to be considered for the leaderboard.
        """
        if not isinstance(min_responses, int):
            raise ValueError("Min responses per matchup must be an integer")

        if min_responses < 3:
            raise ValueError("Min responses per matchup must be at least 3")

        logger.debug(
            f"Setting min responses per matchup to {min_responses} for leaderboard {self.name}"
        )
        self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_response_config_put(
            leaderboard_id=self.id,
            update_leaderboard_response_config_model=UpdateLeaderboardResponseConfigModel(
                responseBudget=self.__response_budget,
                minResponses=min_responses,
            ),
        )
        self.__min_responses_per_matchup = min_responses

    @property
    def show_prompt_asset(self) -> bool:
        """
        Returns whether the prompt asset is shown to the users.
        """
        return self.__show_prompt_asset

    @property
    def inverse_ranking(self) -> bool:
        """
        Returns whether the ranking is inverse.
        """
        return self.__inverse_ranking

    @property
    def show_prompt(self) -> bool:
        """
        Returns whether the prompt is shown to the users.
        """
        return self.__show_prompt

    @property
    def instruction(self) -> str:
        """
        Returns the instruction of the leaderboard.
        """
        return self.__instruction

    @property
    def name(self) -> str:
        """
        Returns the name of the leaderboard.
        """
        return self.__name

    def get_standings(self, tags: Optional[list[str]] = None) -> pd.DataFrame:
        """
        Returns the standings of the leaderboard.

        Args:
            tags: The matchups with these tags should be used to create the standings.
                If tags are None, all matchups will be considered.
                If tags are empty, no matchups will be considered.

        Returns:
            A pandas DataFrame containing the standings of the leaderboard.
        """

        participants = self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_standings_get(
            leaderboard_id=self.id, tags=tags
        )

        standings = []
        for participant in participants.items:
            standings.append(
                {
                    "name": participant.name,
                    "wins": participant.wins,
                    "total_matches": participant.total_matches,
                    "score": (
                        round(participant.score, 2)
                        if participant.score is not None
                        else None
                    ),
                }
            )

        return pd.DataFrame(standings)

    def __str__(self) -> str:
        return f"RapidataLeaderboard(name={self.name}, instruction={self.instruction}, show_prompt={self.show_prompt}, leaderboard_id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
