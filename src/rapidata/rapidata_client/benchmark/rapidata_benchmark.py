import re
from typing import Literal, Optional, Sequence
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.create_leaderboard_model import CreateLeaderboardModel
from rapidata.api_client.models.create_benchmark_participant_model import (
    CreateBenchmarkParticipantModel,
)
from rapidata.api_client.models.submit_prompt_model import SubmitPromptModel
from rapidata.api_client.models.submit_prompt_model_prompt_asset import (
    SubmitPromptModelPromptAsset,
)
from rapidata.api_client.models.url_asset_input import UrlAssetInput
from rapidata.api_client.models.file_asset_model import FileAssetModel
from rapidata.api_client.models.source_url_metadata_model import SourceUrlMetadataModel
from rapidata.api_client.models.and_user_filter_model_filters_inner import (
    AndUserFilterModelFiltersInner,
)

from rapidata.rapidata_client.benchmark.participant._participant import (
    BenchmarkParticipant,
)
from rapidata.rapidata_client.logging import logger
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
    RapidataLeaderboard,
)
from rapidata.rapidata_client.datapoints.assets import MediaAsset
from rapidata.rapidata_client.benchmark._detail_mapper import DetailMapper
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.settings import RapidataSetting


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
        self.__tags: list[list[str]] = []

    def __instantiate_prompts(self) -> None:
        current_page = 1
        total_pages = None

        while True:
            prompts_result = (
                self.__openapi_service.benchmark_api.benchmark_benchmark_id_prompts_get(
                    benchmark_id=self.id,
                    request=QueryModel(page=PageInfo(index=current_page, size=100)),
                )
            )

            if prompts_result.total_pages is None:
                raise ValueError(
                    "An error occurred while fetching prompts: total_pages is None"
                )

            total_pages = prompts_result.total_pages

            for prompt in prompts_result.items:
                self.__prompts.append(prompt.prompt)
                self.__identifiers.append(prompt.identifier)
                if prompt.prompt_asset is None:
                    self.__prompt_assets.append(None)
                else:
                    assert isinstance(
                        prompt.prompt_asset.actual_instance, FileAssetModel
                    )
                    source_url = prompt.prompt_asset.actual_instance.metadata[
                        "sourceUrl"
                    ].actual_instance
                    assert isinstance(source_url, SourceUrlMetadataModel)
                    self.__prompt_assets.append(source_url.url)

                self.__tags.append(prompt.tags)
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
    def tags(self) -> list[list[str]]:
        """
        Returns the tags that are registered for the benchmark.
        """
        if not self.__tags:
            self.__instantiate_prompts()

        return self.__tags

    @property
    def leaderboards(self) -> list[RapidataLeaderboard]:
        """
        Returns the leaderboards that are registered for the benchmark.
        """
        if not self.__leaderboards:
            current_page = 1
            total_pages = None

            while True:
                leaderboards_result = (
                    self.__openapi_service.leaderboard_api.leaderboards_get(
                        request=QueryModel(
                            filter=RootFilter(
                                filters=[
                                    Filter(
                                        field="BenchmarkId",
                                        operator="Eq",
                                        value=self.id,
                                    )
                                ]
                            ),
                            page=PageInfo(index=current_page, size=100),
                        )
                    )
                )

                if leaderboards_result.total_pages is None:
                    raise ValueError(
                        "An error occurred while fetching leaderboards: total_pages is None"
                    )

                total_pages = leaderboards_result.total_pages

                self.__leaderboards.extend(
                    [
                        RapidataLeaderboard(
                            leaderboard.name,
                            leaderboard.instruction,
                            leaderboard.show_prompt,
                            leaderboard.show_prompt_asset,
                            leaderboard.is_inversed,
                            leaderboard.response_budget,
                            leaderboard.min_responses,
                            leaderboard.id,
                            self.__openapi_service,
                        )
                        for leaderboard in leaderboards_result.items
                    ]
                )

                if current_page >= total_pages:
                    break

                current_page += 1

        return self.__leaderboards

    def add_prompt(
        self,
        identifier: str,
        prompt: str | None = None,
        asset: str | None = None,
        tags: Optional[list[str]] = None,
    ):
        """
        Adds a prompt to the benchmark.

        Args:
            identifier: The identifier of the prompt/asset/tags that will be used to match up the media.
            prompt: The prompt that will be used to evaluate the model.
            asset: The asset that will be used to evaluate the model. Provided as a link to the asset.
            tags: The tags can be used to filter the leaderboard results. They will NOT be shown to the users.
        """
        if tags is None:
            tags = []

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

        if asset is not None and not re.match(r"^https?://", asset):
            raise ValueError("Asset must be a link to the asset.")

        if tags is not None and (
            not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags)
        ):
            raise ValueError("Tags must be a list of strings.")

        self.__identifiers.append(identifier)

        self.__tags.append(tags)
        self.__prompts.append(prompt)
        self.__prompt_assets.append(asset)

        self.__openapi_service.benchmark_api.benchmark_benchmark_id_prompt_post(
            benchmark_id=self.id,
            submit_prompt_model=SubmitPromptModel(
                identifier=identifier,
                prompt=prompt,
                promptAsset=(
                    SubmitPromptModelPromptAsset(
                        UrlAssetInput(_t="UrlAssetInput", url=asset)
                    )
                    if asset is not None
                    else None
                ),
                tags=tags,
            ),
        )

    def create_leaderboard(
        self,
        name: str,
        instruction: str,
        show_prompt: bool = False,
        show_prompt_asset: bool = False,
        inverse_ranking: bool = False,
        level_of_detail: Literal["low", "medium", "high", "very high"] = "low",
        min_responses_per_matchup: int = 3,
        validation_set_id: str | None = None,
        filters: Sequence[RapidataFilter] = [],
        settings: Sequence[RapidataSetting] = [],
    ) -> RapidataLeaderboard:
        """
        Creates a new leaderboard for the benchmark.

        Args:
            name: The name of the leaderboard. (not shown to the users)
            instruction: The instruction decides how the models will be evaluated.
            show_prompt: Whether to show the prompt to the users. (default: False)
            show_prompt_asset: Whether to show the prompt asset to the users. (only works if the prompt asset is a URL) (default: False)
            inverse_ranking: Whether to inverse the ranking of the leaderboard. (if the question is inversed, e.g. "Which video is worse?")
            level_of_detail: The level of detail of the leaderboard. This will effect how many comparisons are done per model evaluation. (default: "low")
            min_responses_per_matchup: The minimum number of responses required to be considered for the leaderboard. (default: 3)
            validation_set_id: The id of the validation set that should be attached to the leaderboard. (default: None)
            filters: The filters that should be applied to the leaderboard. Will determine who can solve answer in the leaderboard. (default: [])
            settings: The settings that should be applied to the leaderboard. Will determine the behavior of the tasks on the leaderboard. (default: [])
        """
        if not isinstance(min_responses_per_matchup, int):
            raise ValueError("Min responses per matchup must be an integer")

        if min_responses_per_matchup < 3:
            raise ValueError("Min responses per matchup must be at least 3")

        leaderboard_result = self.__openapi_service.leaderboard_api.leaderboard_post(
            create_leaderboard_model=CreateLeaderboardModel(
                benchmarkId=self.id,
                name=name,
                instruction=instruction,
                showPrompt=show_prompt,
                showPromptAsset=show_prompt_asset,
                isInversed=inverse_ranking,
                minResponses=min_responses_per_matchup,
                responseBudget=DetailMapper.get_budget(level_of_detail),
                validationSetId=validation_set_id,
                filters=(
                    [
                        AndUserFilterModelFiltersInner(filter._to_model())
                        for filter in filters
                    ]
                    if filters
                    else None
                ),
                featureFlags=(
                    [setting._to_feature_flag() for setting in settings]
                    if settings
                    else None
                ),
            )
        )

        assert (
            leaderboard_result.benchmark_id == self.id
        ), "The leaderboard was not created for the correct benchmark."

        return RapidataLeaderboard(
            name,
            instruction,
            show_prompt,
            show_prompt_asset,
            inverse_ranking,
            leaderboard_result.response_budget,
            min_responses_per_matchup,
            leaderboard_result.id,
            self.__openapi_service,
        )

    def evaluate_model(
        self, name: str, media: list[str], identifiers: list[str]
    ) -> None:
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
            raise ValueError(
                "All identifiers must be in the registered identifiers list. To see the registered identifiers, use the identifiers property.\
\nTo see the prompts that are associated with the identifiers, use the prompts property."
            )

        # happens before the creation of the participant to ensure all media paths are valid
        assets: list[MediaAsset] = []
        for media_path in media:
            assets.append(MediaAsset(media_path))

        participant_result = self.__openapi_service.benchmark_api.benchmark_benchmark_id_participants_post(
            benchmark_id=self.id,
            create_benchmark_participant_model=CreateBenchmarkParticipantModel(
                name=name,
            ),
        )

        logger.info(f"Participant created: {participant_result.participant_id}")

        participant = BenchmarkParticipant(
            name, participant_result.participant_id, self.__openapi_service
        )

        successful_uploads, failed_uploads = participant.upload_media(
            assets,
            identifiers,
        )

        total_uploads = len(assets)
        success_rate = (
            (len(successful_uploads) / total_uploads * 100) if total_uploads > 0 else 0
        )
        logger.info(
            f"Upload complete: {len(successful_uploads)} successful, {len(failed_uploads)} failed ({success_rate:.1f}% success rate)"
        )

        if failed_uploads:
            logger.error(
                f"Failed uploads for media: {[asset.path for asset in failed_uploads]}"
            )
            logger.warning(
                "Some uploads failed. The model evaluation may be incomplete."
            )

        if len(successful_uploads) == 0:
            raise RuntimeError(
                "No uploads were successful. The model evaluation will not be completed."
            )

        self.__openapi_service.participant_api.participants_participant_id_submit_post(
            participant_id=participant_result.participant_id
        )

    def __str__(self) -> str:
        return f"RapidataBenchmark(name={self.name}, id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
