from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.leaderboard.rapidata_leaderboard import RapidataLeaderboard
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion

class RapidataLeaderboardManager:
    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
    
    def create_new_leaderboard(self, leaderboard_name: str, instruction: str, prompts: list[str], show_prompt: bool = False) -> RapidataLeaderboard:
        leaderboard = RapidataLeaderboard(leaderboard_name, instruction, show_prompt, None, self._openapi_service)
        leaderboard._register_prompts(prompts)
        return leaderboard
    
    def get_leaderboard_by_id(self, leaderboard_id: str) -> RapidataLeaderboard:
        leaderboard_result = self._openapi_service.leaderboard_api.leaderboard_leaderboard_id_get(
            leaderboard_id=leaderboard_id
        )
        return RapidataLeaderboard(leaderboard_result.name, leaderboard_result.instruction, leaderboard_result.show_prompt, leaderboard_id, self._openapi_service)
    
    def find_leaderboards(self, name: str = "", amount: int = 10) -> list[RapidataLeaderboard]:
        leaderboard_result = self._openapi_service.leaderboard_api.leaderboards_get(
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
            leaderboards.append(RapidataLeaderboard(leaderboard.name, leaderboard.instruction, leaderboard.show_prompt, leaderboard.id, self._openapi_service))
        return leaderboards
            
