from rapidata.api_client.models.create_leaderboard_participant_model import CreateLeaderboardParticipantModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.query_model import QueryModel

from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.assets import MediaAsset
from rapidata.rapidata_client.metadata import PromptMetadata
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
    def __init__(self, name: str, instruction: str, show_prompt: bool, id: str, openapi_service: OpenAPIService):
        self.__openapi_service = openapi_service
        self.name = name
        self.instruction = instruction
        self.show_prompt = show_prompt
        self._prompts: list[str] = []
        self.id = id

    @property
    def prompts(self) -> list[str]:
        """
        Returns the prompts that are registered for the leaderboard.
        """
        if not self._prompts:
            current_page = 1
            total_pages = None
            
            while True:
                prompts_result = self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_prompts_get(
                    leaderboard_id=self.id,
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
    
    def _register_prompts(self, prompts: list[str]):
        """
        Registers the prompts for the leaderboard.
        """
        for prompt in prompts:
            self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_prompts_post(
                leaderboard_id=self.id,
                body=prompt
            )
        self._prompts = prompts

    def evaluate_model(self, name: str, media: list[str], prompts: list[str]) -> None:
        """
        Evaluates a model on the leaderboard.

        Args:
            name: The name of the model.
            media: The generated images/videos that will be used to evaluate the model.
            prompts: The prompts that correspond to the media. The order of the prompts must match the order of the media.
                The prompts that are used must be registered for the leaderboard. To see the registered prompts, use the prompts property.
        """
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

        participant_result = self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_participants_post(
            leaderboard_id=self.id,
            create_leaderboard_participant_model=CreateLeaderboardParticipantModel(
                name=name,
            )
        )
        dataset = RapidataDataset(participant_result.dataset_id, self.__openapi_service)

        dataset._add_datapoints(assets, prompts_metadata)

        self.__openapi_service.leaderboard_api.leaderboard_leaderboard_id_participants_participant_id_submit_post(
            leaderboard_id=self.id,
            participant_id=participant_result.participant_id
        )

    def __str__(self) -> str:
        return f"RapidataLeaderboard(name={self.name}, instruction={self.instruction}, show_prompt={self.show_prompt}, leaderboard_id={self.id})"
    
    def __repr__(self) -> str:
        return self.__str__()


        


