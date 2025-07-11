from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.create_leaderboard_model import CreateLeaderboardModel
from rapidata.api_client.models.create_benchmark_participant_model import CreateBenchmarkParticipantModel
from rapidata.api_client.models.submit_prompt_model import SubmitPromptModel

from rapidata.rapidata_client.logging import logger
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import RapidataLeaderboard
from rapidata.rapidata_client.metadata import PromptIdentifierMetadata
from rapidata.rapidata_client.assets import MediaAsset
from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset

class RapidataBenchmark:
    """
    An instance of a Rapidata benchmark.

    Used to interact with a specific benchmark in the Rapidata system, such as retrieving prompts and evaluating models.

    Args:
        name: The name that will be used to identify the benchmark on the overview.
        id: The id of the benchmark.
        openapi_service: The OpenAPI service to use to interact with the Rapidata API.
    """
    def __init__(self, name: str, id: str, openapi_service: OpenAPIService):
        self.name = name
        self.id = id
        self.__openapi_service = openapi_service
        self.__prompts: list[str] = []
        self.__leaderboards: list[RapidataLeaderboard] = []
        self.__identifiers: list[str] = []

    def __instantiate_prompts(self) -> None:
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
            self.__identifiers.extend([prompt.identifier for prompt in prompts_result.items])
            
            if current_page >= total_pages:
                break
                
            current_page += 1

    @property
    def prompts(self) -> list[str]:
        """
        Returns the prompts that are registered for the leaderboard.
        """
        if not self.__prompts:
            self.__instantiate_prompts()
        
        return self.__prompts
    
    @property
    def identifiers(self) -> list[str]:
        if not self.__identifiers:
            self.__instantiate_prompts()
        
        return self.__identifiers
    
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
    
    def add_prompt(self, identifier: str, prompt: str):
        """
        Adds a prompt to the benchmark.
        """
        if not isinstance(identifier, str) or not isinstance(prompt, str):
            raise ValueError("Identifier and prompt must be strings.")
        
        if identifier in self.identifiers:
            raise ValueError("Identifier already exists in the benchmark.")
        
        self.__identifiers.append(identifier)
        self.__prompts.append(prompt)

        self.__openapi_service.benchmark_api.benchmark_benchmark_id_prompt_post(
            benchmark_id=self.id,
            submit_prompt_model=SubmitPromptModel(
                identifier=identifier,
                prompt=prompt,
            )
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
    
    def evaluate_model(self, name: str, media: list[str], identifiers: list[str]) -> None:
        """
        Evaluates a model on the benchmark across all leaderboards.

        Args:
            name: The name of the model.
            media: The generated images/videos that will be used to evaluate the model.
            identifiers: The identifiers that correspond to the media. The order of the identifiers must match the order of the media.
                The identifiers that are used must be registered for the benchmark. To see the registered identifiers, use the identifiers property.
        """
        if not media:
            raise ValueError("Media must be a non-empty list of strings")
        
        if len(media) != len(identifiers):
            raise ValueError("Media and identifiers must have the same length")
        
        if not all(identifier in self.identifiers for identifier in identifiers):
            raise ValueError("All identifiers must be in the registered identifiers list. To see the registered identifiers, use the identifiers property.\
\nTo see the prompts that are associated with the identifiers, use the prompts property.")
        
        # happens before the creation of the participant to ensure all media paths are valid
        assets = []
        prompts_metadata: list[list[PromptIdentifierMetadata]] = []
        for media_path, identifier in zip(media, identifiers):
            assets.append(MediaAsset(media_path))
            prompts_metadata.append([PromptIdentifierMetadata(identifier=identifier)])

        participant_result = self.__openapi_service.benchmark_api.benchmark_benchmark_id_participants_post(
            benchmark_id=self.id,
            create_benchmark_participant_model=CreateBenchmarkParticipantModel(
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

    def __str__(self) -> str:
        return f"RapidataBenchmark(name={self.name}, id={self.id})"
    
    def __repr__(self) -> str:
        return self.__str__()
