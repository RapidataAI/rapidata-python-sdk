import re
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.create_leaderboard_model import CreateLeaderboardModel
from rapidata.api_client.models.create_benchmark_participant_model import CreateBenchmarkParticipantModel
from rapidata.api_client.models.submit_prompt_model import SubmitPromptModel
from rapidata.api_client.models.submit_prompt_model_prompt_asset import SubmitPromptModelPromptAsset
from rapidata.api_client.models.url_asset_input import UrlAssetInput
from rapidata.api_client.models.file_asset_model import FileAssetModel
from rapidata.api_client.models.source_url_metadata_model import SourceUrlMetadataModel

from rapidata.rapidata_client.logging import logger
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import RapidataLeaderboard
from rapidata.rapidata_client.datapoints.metadata import PromptIdentifierMetadata
from rapidata.rapidata_client.datapoints.assets import MediaAsset
from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.datapoints.datapoint import Datapoint

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
        self.__prompts: list[str | None] = []
        self.__prompt_assets: list[str | None] = []
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
            
            for prompt in prompts_result.items:
                self.__prompts.append(prompt.prompt)
                self.__identifiers.append(prompt.identifier)
                if prompt.prompt_asset is None:
                    self.__prompt_assets.append(None)
                else:
                    assert isinstance(prompt.prompt_asset.actual_instance, FileAssetModel)
                    source_url = prompt.prompt_asset.actual_instance.metadata["sourceUrl"].actual_instance
                    assert isinstance(source_url, SourceUrlMetadataModel)
                    self.__prompt_assets.append(source_url.url)
            
            if current_page >= total_pages:
                break
                
            current_page += 1

    @property
    def identifiers(self) -> list[str]:
        if not self.__identifiers:
            self.__instantiate_prompts()
        
        return self.__identifiers
    
    @property
    def prompts(self) -> list[str | None]:
        """
        Returns the prompts that are registered for the leaderboard.
        """
        if not self.__prompts:
            self.__instantiate_prompts()
        
        return self.__prompts
    
    @property
    def prompt_assets(self) -> list[str | None]:
        """
        Returns the prompt assets that are registered for the benchmark.
        """
        if not self.__prompt_assets:
            self.__instantiate_prompts()
        
        return self.__prompt_assets
    
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
                        leaderboard.show_prompt_asset,
                        leaderboard.is_inversed,
                        leaderboard.min_responses,
                        leaderboard.response_budget,
                        leaderboard.id, 
                        self.__openapi_service
                        ) for leaderboard in leaderboards_result.items])
                
                if current_page >= total_pages:
                    break
                    
                current_page += 1
                
        return self.__leaderboards
    
    def add_prompt(self, identifier: str, prompt: str | None = None, asset: str | None = None):
        """
        Adds a prompt to the benchmark.

        Args:
            identifier: The identifier of the prompt/asset that will be used to match up the media.
            prompt: The prompt that will be used to evaluate the model.
            asset: The asset that will be used to evaluate the model. Provided as a link to the asset.
        """
        if not isinstance(identifier, str):
            raise ValueError("Identifier must be a string.")
        
        if prompt is None and asset is None:
            raise ValueError("Prompt or asset must be provided.")
        
        if prompt is not None and not isinstance(prompt, str):
            raise ValueError("Prompt must be a string.")
        
        if asset is not None and not isinstance(asset, str):
            raise ValueError("Asset must be a string. That is the link to the asset.")
        
        if identifier in self.identifiers:
            raise ValueError("Identifier already exists in the benchmark.")
        
        if asset is not None and not re.match(r'^https?://', asset):
            raise ValueError("Asset must be a link to the asset.")
        
        self.__identifiers.append(identifier)

        self.__prompts.append(prompt)
        self.__prompt_assets.append(asset)

        self.__openapi_service.benchmark_api.benchmark_benchmark_id_prompt_post(
            benchmark_id=self.id,
            submit_prompt_model=SubmitPromptModel(
                identifier=identifier,
                prompt=prompt,
                promptAsset=SubmitPromptModelPromptAsset(
                    UrlAssetInput(
                        _t="UrlAssetInput",
                        url=asset
                    )
                ) if asset is not None else None
            )
        )

    def create_leaderboard(
        self, 
        name: str, 
        instruction: str, 
        show_prompt: bool = False,
        show_prompt_asset: bool = False,
        inverse_ranking: bool = False,
        min_responses: int | None = None,
        response_budget: int | None = None
    ) -> RapidataLeaderboard:
        """
        Creates a new leaderboard for the benchmark.

        Args:
            name: The name of the leaderboard. (not shown to the users)
            instruction: The instruction decides how the models will be evaluated.
            show_prompt: Whether to show the prompt to the users. (default: False)
            show_prompt_asset: Whether to show the prompt asset to the users. (only works if the prompt asset is a URL) (default: False)
            inverse_ranking: Whether to inverse the ranking of the leaderboard. (if the question is inversed, e.g. "Which video is worse?")
            min_responses: The minimum amount of responses that get collected per comparison. if None, it will be defaulted.
            response_budget: The total amount of responses that get collected per new model evaluation. if None, it will be defaulted. Values below 2000 are not recommended.
        """

        if response_budget is not None and response_budget < 2000:
            logger.warning("Response budget is below 2000. This is not recommended.")

        leaderboard_result = self.__openapi_service.leaderboard_api.leaderboard_post(
            create_leaderboard_model=CreateLeaderboardModel(
                benchmarkId=self.id,
                name=name,
                instruction=instruction,
                showPrompt=show_prompt,
                showPromptAsset=show_prompt_asset,
                isInversed=inverse_ranking,
                minResponses=min_responses,
                responseBudget=response_budget
            )
        )

        assert leaderboard_result.benchmark_id == self.id, "The leaderboard was not created for the correct benchmark."

        return RapidataLeaderboard(
            name,
            instruction,
            show_prompt,
            show_prompt_asset,
            inverse_ranking,
            leaderboard_result.min_responses,
            leaderboard_result.response_budget,
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
            dataset.add_datapoints([Datapoint(asset=asset, metadata=metadata) for asset, metadata in zip(assets, prompts_metadata)])
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
