import urllib.parse
import webbrowser
from colorama import Fore
import pandas as pd
from typing import Literal, Optional

from rapidata.rapidata_client.config import logger, managed_print, tracer
from rapidata.rapidata_client.benchmark._detail_mapper import DetailMapper
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.update_leaderboard_model import UpdateLeaderboardModel


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
        benchmark_id: str,
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
        self.__benchmark_id = benchmark_id
        self.id = id
        self.__leaderboard_page = f"https://app.{self.__openapi_service.environment}/mri/benchmarks/{self.__benchmark_id}/leaderboard/{self.id}"

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
        with tracer.start_as_current_span("RapidataLeaderboard.level_of_detail.setter"):
            logger.debug(f"Setting level of detail to {level_of_detail}")
            self.__response_budget = DetailMapper.get_budget(level_of_detail)
            self._update_config()

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
        with tracer.start_as_current_span(
            "RapidataLeaderboard.min_responses_per_matchup.setter"
        ):
            if not isinstance(min_responses, int):
                raise ValueError("Min responses per matchup must be an integer")

            if min_responses < 3:
                raise ValueError("Min responses per matchup must be at least 3")

            logger.debug(
                f"Setting min responses per matchup to {min_responses} for leaderboard {self.name}"
            )
            self.__min_responses_per_matchup = min_responses
            self._update_config()

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

    @name.setter
    def name(self, name: str):
        """
        Sets the name of the leaderboard.
        """
        with tracer.start_as_current_span("RapidataLeaderboard.name.setter"):
            if not isinstance(name, str):
                raise ValueError("Name must be a string")
            if len(name) < 1:
                raise ValueError("Name must be at least 1 character long")

            self.__name = name
            self._update_config()

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
        with tracer.start_as_current_span("RapidataLeaderboard.get_standings"):
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

    def view(self) -> None:
        """
        Views the leaderboard.
        """
        logger.info("Opening leaderboard page in browser...")
        could_open_browser = webbrowser.open(self.__leaderboard_page)
        if not could_open_browser:
            encoded_url = urllib.parse.quote(
                self.__leaderboard_page, safe="%/:=&?~#+!$,;'@()*[]"
            )
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )

    def _custom_config(self, response_budget: int, min_responses_per_matchup: int):
        self.__response_budget = response_budget
        self.__min_responses_per_matchup = min_responses_per_matchup
        self._update_config()

    def _update_config(self):
        with tracer.start_as_current_span("RapidataLeaderboard._update_config"):
            self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_patch(
                leaderboard_id=self.id,
                update_leaderboard_model=UpdateLeaderboardModel(
                    name=self.__name,
                    responseBudget=self.__response_budget,
                    minResponses=self.__min_responses_per_matchup,
                ),
            )

    def __str__(self) -> str:
        return f"RapidataLeaderboard(name={self.name}, instruction={self.instruction}, show_prompt={self.show_prompt}, leaderboard_id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
