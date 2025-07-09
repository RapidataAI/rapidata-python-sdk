from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.create_leaderboard_model import CreateLeaderboardModel
from rapidata.api_client.models.create_leaderboard_participant_model import CreateLeaderboardParticipantModel

from rapidata.rapidata_client.logging import logger
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import RapidataLeaderboard
from rapidata.rapidata_client.metadata import PromptMetadata
from rapidata.rapidata_client.assets import MediaAsset
from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset

class RapidataBenchmark:
    """
    An instance of a Rapidata benchmark.

    Used to interact with a specific benchmark in the Rapidata system, such as retrieving prompts and evaluating models.

    Args:
        name: The name that will be used to identify the benchmark on the overview.
        prompts: The prompts that will be registered for the benchmark.
        leaderboards: The leaderboards that will be registered for the benchmark.
    """
    def __init__(self, name: str, id: str, openapi_service: OpenAPIService):
        self.name = name
        self.id = id
        self.__openapi_service = openapi_service
        self.__prompts = []
        self.__leaderboards = []

    @property
    def prompts(self) -> list[str]:
        """
        Returns the prompts that are registered for the leaderboard.
        """
        if not self.__prompts:
            current_page = 1
            total_pages = None
            
            while True:
                prompts_result = self.__openapi_service.benchmark_api.benchmark_benchmark_id_prompts_get(
                    benchmark_id=self.id,
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
                
                self.__prompts.extend([prompt.prompt for prompt in prompts_result.items])
                
                if current_page >= total_pages:
                    break
                    
                current_page += 1
                
        return self.__prompts
    
    @property
    def leaderboards(self) -> list[RapidataLeaderboard]:
        """
        Returns the leaderboards that are registered for the benchmark.
        """
        if not self.__leaderboards:
            current_page = 1
            total_pages = None
            
            while True:
                leaderboards_result = self.__openapi_service.leaderboard_api.leaderboards_get(
                    request=QueryModel(
                        filter=RootFilter(
                            filters=[
                                Filter(field="BenchmarkId", operator="Eq", value=self.id)
                                ]
                            ),
                        page=PageInfo(
                            index=current_page,
                            size=100
                        )
                    )
                )
                
                if leaderboards_result.total_pages is None:
                    raise ValueError("An error occurred while fetching leaderboards: total_pages is None")
                
                total_pages = leaderboards_result.total_pages
                
                self.__leaderboards.extend([
                    RapidataLeaderboard(
                        leaderboard.name, 
                        leaderboard.instruction, 
                        leaderboard.show_prompt, 
                        leaderboard.id, 
                        self.__openapi_service
                        ) for leaderboard in leaderboards_result.items])
                
                if current_page >= total_pages:
                    break
                    
                current_page += 1
                
        return self.__leaderboards
    
    def add_prompt(self, prompt: str):
        self.__openapi_service.benchmark_api.benchmark_benchmark_id_prompt_post(
            benchmark_id=self.id,
            body=prompt
        )

    def create_leaderboard(self, name: str, instruction: str, show_prompt: bool) -> RapidataLeaderboard:
        """
        Creates a new leaderboard for the benchmark.
        """
        leaderboard_result = self.__openapi_service.leaderboard_api.leaderboard_post(
            create_leaderboard_model=CreateLeaderboardModel(
                benchmarkId=self.id,
                name=name,
                instruction=instruction,
                showPrompt=show_prompt
            )
        )

        assert leaderboard_result.benchmark_id == self.id, "The leaderboard was not created for the correct benchmark."

        return RapidataLeaderboard(
            name,
            instruction,
            show_prompt,
            leaderboard_result.id,
            self.__openapi_service
        )
    
    def evaluate_model(self, name: str, media: list[str], prompts: list[str]) -> None:
        """
        Evaluates a model on the benchmark across all leaderboards.

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
            prompts_metadata.append([PromptMetadata(prompt=prompt)])

        participant_result = self.__openapi_service.benchmark_api.benchmark_benchmark_id_participants_post(
            benchmark_id=self.id,
            create_leaderboard_participant_model=CreateLeaderboardParticipantModel(
                name=name,
            )
        )

        dataset = RapidataDataset(participant_result.dataset_id, self.__openapi_service)
        
        try:
            dataset._add_datapoints(assets, prompts_metadata)
        except Exception as e:
            logger.warning(f"An error occurred while adding datapoints to the dataset: {e}")
            upload_progress = self.__openapi_service.dataset_api.dataset_dataset_id_progress_get(
                dataset_id=dataset.id
            )
            if upload_progress.ready == 0:
                raise RuntimeError("None of the media was uploaded successfully. Please check the media paths and try again.")
            
            logger.warning(f"{upload_progress.failed} datapoints failed to upload. \n{upload_progress.ready} datapoints were uploaded successfully. \nEvaluation will continue with the uploaded datapoints.")

        self.__openapi_service.benchmark_api.benchmark_benchmark_id_participants_participant_id_submit_post(
            benchmark_id=self.id,
            participant_id=participant_result.participant_id
        )
