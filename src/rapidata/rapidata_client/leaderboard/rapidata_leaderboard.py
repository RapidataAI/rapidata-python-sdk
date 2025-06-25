from rapidata.api_client.models.create_leaderboard_model import CreateLeaderboardModel
from rapidata.api_client.models.create_leaderboard_participant_model import CreateLeaderboardParticipantModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.query_model import QueryModel

from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.assets import MediaAsset
from rapidata.rapidata_client.metadata import PromptMetadata
from rapidata.service.openapi_service import OpenAPIService


class RapidataLeaderboard:
    def __init__(self, name: str, instruction: str, show_prompt: bool, leaderboard_id: str | None, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        self._name = name
        self._instruction = instruction
        self._show_prompt = show_prompt
        self._prompts: list[str] = []
        if leaderboard_id is None:
            self.leaderboard_id = self.__create_new_leaderboard()
        else:
            self.leaderboard_id = leaderboard_id

    @property
    def prompts(self) -> list[str]:
        if not self._prompts:
            current_page = 1
            total_pages = None
            
            while True:
                prompts_result = self._openapi_service.leaderboard_api.leaderboard_leaderboard_id_prompts_get(
                    leaderboard_id=self.leaderboard_id,
                    request=QueryModel(
                        page=PageInfo(
                            index=current_page,
                            size=100
                        )
                    )
                )
                
                if prompts_result.total_pages is None:
                    raise ValueError("An error occurred while fetching prompts: total_pages is None")
                
                total_pages = prompts_result.total_pages
                
                self._prompts.extend([prompt.prompt for prompt in prompts_result.items])
                
                if current_page >= total_pages:
                    break
                    
                current_page += 1
                
        return self._prompts
    def __create_new_leaderboard(self) -> str:
        leaderboard_id = self._openapi_service.leaderboard_api.leaderboard_post(
            CreateLeaderboardModel(
                name=self._name,
                instruction=self._instruction,
                showPrompt=self._show_prompt
            )
        ).id
        return leaderboard_id
    
    def _register_prompts(self, prompts: list[str]):
        for prompt in prompts:
            self._openapi_service.leaderboard_api.leaderboard_leaderboard_id_prompts_post(
                leaderboard_id=self.leaderboard_id,
                body=prompt
            )
        self._prompts = prompts

    def evaluate_model(self, name: str, media: list[str], prompts: list[str]) -> None:
        if not media:
            raise ValueError("Media must be a non-empty list of strings")
        
        if len(media) != len(prompts):
            raise ValueError("Media and prompts must have the same length")
        
        if not all(prompt in self.prompts for prompt in prompts):
            raise ValueError("All prompts must be in the registered prompts list. To see the registered prompts, use the prompts property.")
        
        # happens before the creation of the participant to ensure all media paths are valid
        assets = []
        prompts_metadata: list[list[PromptMetadata]] = []
        for media_path, prompt in zip(media, prompts):
            assets.append(MediaAsset(media_path))
            prompts_metadata.append([PromptMetadata(prompt)])

        participant_result = self._openapi_service.leaderboard_api.leaderboard_leaderboard_id_participants_post(
            leaderboard_id=self.leaderboard_id,
            create_leaderboard_participant_model=CreateLeaderboardParticipantModel(
                name=name,
            )
        )
        dataset = RapidataDataset(participant_result.dataset_id, self._openapi_service)

        dataset._add_datapoints(assets, prompts_metadata)

        self._openapi_service.leaderboard_api.leaderboard_leaderboard_id_participants_participant_id_submit_post(
            leaderboard_id=self.leaderboard_id,
            participant_id=participant_result.participant_id
        )

    def __str__(self) -> str:
        return f"RapidataLeaderboard(name={self._name}, instruction={self._instruction}, show_prompt={self._show_prompt}, leaderboard_id={self.leaderboard_id})"
    
    def __repr__(self) -> str:
        return self.__str__()


        


