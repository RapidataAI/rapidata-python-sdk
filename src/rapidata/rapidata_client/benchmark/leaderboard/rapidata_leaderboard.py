import pandas as pd

from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.sort_criterion import SortCriterion

from rapidata.service.openapi_service import OpenAPIService


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
    def __init__(self, 
                 name: str, 
                 instruction: str, 
                 show_prompt: bool, 
                 show_prompt_asset: bool,
                 inverse_ranking: bool, 
                 min_responses: int,
                 response_budget: int,
                 id: str, 
                 openapi_service: OpenAPIService):
        self.__openapi_service = openapi_service
        self.__name = name
        self.__instruction = instruction
        self.__show_prompt = show_prompt
        self.__show_prompt_asset = show_prompt_asset
        self.__inverse_ranking = inverse_ranking
        self.__min_responses = min_responses
        self.__response_budget = response_budget
        self.id = id

    @property
    def response_budget(self) -> int:
        """
        Returns the response budget of the leaderboard.
        """
        return self.__response_budget
    
    @property
    def min_responses(self) -> int:
        """
        Returns the minimum number of responses required to be considered for the leaderboard.
        """
        return self.__min_responses
    
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

    def get_standings(self) -> pd.DataFrame:
        """
        Returns the standings of the leaderboard.
        """
        participants = self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_standings_get(
            leaderboard_id=self.id,
            request=QueryModel(
                page=PageInfo(index=1, size=1000),
                sortCriteria=[SortCriterion(direction="Desc", propertyName="Score")]
            )
        )

        standings = []
        for participant in participants.items:
            standings.append({
                "name": participant.name,
                "wins": participant.wins,
                "total_matches": participant.total_matches,
                "score": round(participant.score, 2) if participant.score is not None else None,
            })

        return pd.DataFrame(standings)

    def __str__(self) -> str:
        return f"RapidataLeaderboard(name={self.name}, instruction={self.instruction}, show_prompt={self.show_prompt}, leaderboard_id={self.id})"
    
    def __repr__(self) -> str:
        return self.__str__()


        


