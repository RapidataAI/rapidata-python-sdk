from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.leaderboard.rapidata_leaderboard import RapidataLeaderboard
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion
from rapidata.api_client.models.create_leaderboard_model import CreateLeaderboardModel

class RapidataLeaderboardManager:
    """
    A manager for leaderboards.

    Used to create and retrieve leaderboards.

    Args:
        openapi_service: The OpenAPIService instance for API interaction.
    """
    def __init__(self, openapi_service: OpenAPIService):
        self.__openapi_service = openapi_service

    def create_new_leaderboard(self, name: str, instruction: str, prompts: list[str], show_prompt: bool = False) -> RapidataLeaderboard:
        """
        Creates a new leaderboard with the given name, instruction, and prompts.

        Args:
            leaderboard_name: The name of the leaderboard. Will be used to identify the leaderboard on the overview.
            instruction: The instruction for the leaderboard. Will determine how the models will be evaluated.
            prompts: The prompts for the leaderboard. Will be registered for the leaderboard and able to be retrieved again later.
            show_prompt: Whether to show the prompt to the users when they are evaluating the models.
        """
        if not isinstance(name, str):
            raise ValueError("Name must be a string.")
        
        if not isinstance(instruction, str):
            raise ValueError("Instruction must be a string.")
        
        if not isinstance(show_prompt, bool):
            raise ValueError("Show prompt must be a boolean.")
        
        if not isinstance(prompts, list) or not all(isinstance(prompt, str) for prompt in prompts):
            raise ValueError("Prompts must be a list of strings.")

        leaderboard_id = self.__register_new_leaderboard(name, instruction, show_prompt)
        leaderboard = RapidataLeaderboard(name, instruction, show_prompt, leaderboard_id, self.__openapi_service)
        leaderboard._register_prompts(prompts)
        return leaderboard
    
    def get_leaderboard_by_id(self, leaderboard_id: str) -> RapidataLeaderboard:
        """
        Retrieves a leaderboard by its ID.

        Args:
            leaderboard_id: The ID of the leaderboard.
        """
        leaderboard_result = self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_get(
            leaderboard_id=leaderboard_id
        )
        return RapidataLeaderboard(leaderboard_result.name, leaderboard_result.instruction, leaderboard_result.show_prompt, leaderboard_id, self.__openapi_service)
    
    def find_leaderboards(self, name: str = "", amount: int = 10) -> list[RapidataLeaderboard]:
        """
        Find your recent leaderboards given criteria. If nothing is provided, it will return the most recent leaderboard.

        Args:
            name (str, optional): The name of the leaderboard - matching leaderboard will contain the name. Defaults to "" for any leaderboard.
            amount (int, optional): The amount of leaderboards to return. Defaults to 10.
        """
        leaderboard_result = self.__openapi_service.leaderboard_api.leaderboards_get(
            request=QueryModel(
                page=PageInfo(
                    index=1,
                    size=amount
                ),
                filter=RootFilter(filters=[Filter(field="Name", operator="Contains", value=name)]),
                sortCriteria=[SortCriterion(direction="Desc", propertyName="CreatedAt")]
            )
        )
        leaderboards = []
        for leaderboard in leaderboard_result.items:
            leaderboards.append(RapidataLeaderboard(leaderboard.name, leaderboard.instruction, leaderboard.show_prompt, leaderboard.id, self.__openapi_service))
        return leaderboards

    def __register_new_leaderboard(self, name: str, instruction: str, show_prompt: bool) -> str:
        leaderboard_id = self.__openapi_service.leaderboard_api.leaderboard_post(
            CreateLeaderboardModel(
                name=name,
                instruction=instruction,
                showPrompt=show_prompt
            )
        ).id
        return leaderboard_id
