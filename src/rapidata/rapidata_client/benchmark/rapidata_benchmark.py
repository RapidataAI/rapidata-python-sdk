import pandas as pd
import urllib.parse
import webbrowser
from colorama import Fore
from typing import Literal, Optional, Sequence

from rapidata.api_client.models.and_user_filter_model_filters_inner import (
    AndUserFilterModelFiltersInner,
)
from rapidata.api_client.models.create_benchmark_participant_model import (
    CreateBenchmarkParticipantModel,
)
from rapidata.api_client.models.create_leaderboard_model import CreateLeaderboardModel
from rapidata.api_client.models.file_asset_model import FileAssetModel
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.source_url_metadata_model import SourceUrlMetadataModel
from rapidata.api_client.models.submit_prompt_model import SubmitPromptModel
from rapidata.api_client.models.existing_asset_input import ExistingAssetInput
from rapidata.api_client.models.create_datapoint_model_context_asset import (
    CreateDatapointModelContextAsset,
)
from rapidata.rapidata_client.benchmark._detail_mapper import DetailMapper
from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
    RapidataLeaderboard,
)
from rapidata.rapidata_client.benchmark.participant._participant import (
    BenchmarkParticipant,
)
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.config import logger, managed_print, tracer
from rapidata.rapidata_client.settings import RapidataSetting
from rapidata.service.openapi_service import OpenAPIService


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
        self._openapi_service = openapi_service
        self.__prompts: list[str | None] = []
        self.__prompt_assets: list[str | None] = []
        self.__leaderboards: list[RapidataLeaderboard] = []
        self.__identifiers: list[str] = []
        self.__tags: list[list[str]] = []
        self.__benchmark_page: str = (
            f"https://app.{self._openapi_service.environment}/mri/benchmarks/{self.id}"
        )
        self._asset_uploader = AssetUploader(openapi_service)

    def __instantiate_prompts(self) -> None:
        with tracer.start_as_current_span("RapidataBenchmark.__instantiate_prompts"):
            current_page = 1
            total_pages = None

            while True:
                prompts_result = self._openapi_service.benchmark_api.benchmark_benchmark_id_prompts_get(
                    benchmark_id=self.id,
                    request=QueryModel(page=PageInfo(index=current_page, size=100)),
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
        with tracer.start_as_current_span("RapidataBenchmark.leaderboards"):
            if not self.__leaderboards:
                current_page = 1
                total_pages = None

                while True:
                    leaderboards_result = self._openapi_service.benchmark_api.benchmark_benchmark_id_leaderboards_get(
                        benchmark_id=self.id,
                        request=QueryModel(
                            page=PageInfo(index=current_page, size=100),
                        ),
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
                                self.id,
                                leaderboard.id,
                                self._openapi_service,
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
        identifier: str | None = None,
        prompt: str | None = None,
        prompt_asset: str | None = None,
        tags: Optional[list[str]] = None,
    ):
        """
        Adds a prompt to the benchmark.

        Args:
            identifier: The identifier of the prompt/asset/tags that will be used to match up the media. If not provided, it will use the prompt, asset or prompt + asset as the identifier.
            prompt: The prompt that will be used to evaluate the model.
            prompt_asset: The prompt asset that will be used to evaluate the model. Provided as a link to the asset.
            tags: The tags can be used to filter the leaderboard results. They will NOT be shown to the users.
        """
        with tracer.start_as_current_span("RapidataBenchmark.add_prompt"):
            if tags is None:
                tags = []

            if prompt is None and prompt_asset is None:
                raise ValueError("Prompt or prompt asset must be provided.")

            if identifier is None and prompt is None:
                raise ValueError("Identifier or prompt must be provided.")

            if identifier and not isinstance(identifier, str):
                raise ValueError("Identifier must be a string.")

            if prompt and not isinstance(prompt, str):
                raise ValueError("Prompt must be a string.")

            if prompt_asset and not isinstance(prompt_asset, str):
                raise ValueError(
                    "Asset must be a string. That is the link to the asset."
                )

            if identifier is None:
                assert prompt is not None
                if prompt in self.prompts:
                    raise ValueError(
                        "Prompts must be unique. Otherwise use identifiers."
                    )
                identifier = prompt

            if identifier in self.identifiers:
                raise ValueError("Identifier already exists in the benchmark.")

            if tags is not None and (
                not isinstance(tags, list)
                or not all(isinstance(tag, str) for tag in tags)
            ):
                raise ValueError("Tags must be a list of strings.")

            logger.info(
                "Adding identifier %s with prompt %s, prompt asset %s and tags %s to benchmark %s",
                identifier,
                prompt,
                prompt_asset,
                tags,
                self.id,
            )

            self.__identifiers.append(identifier)

            self.__tags.append(tags)
            self.__prompts.append(prompt)
            self.__prompt_assets.append(prompt_asset)

            self._openapi_service.benchmark_api.benchmark_benchmark_id_prompt_post(
                benchmark_id=self.id,
                submit_prompt_model=SubmitPromptModel(
                    identifier=identifier,
                    prompt=prompt,
                    promptAsset=(
                        CreateDatapointModelContextAsset(
                            actual_instance=ExistingAssetInput(
                                _t="ExistingAssetInput",
                                name=self._asset_uploader.upload_asset(prompt_asset),
                            )
                        )
                        if prompt_asset is not None
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
        with tracer.start_as_current_span("create_leaderboard"):
            if not isinstance(min_responses_per_matchup, int):
                raise ValueError("Min responses per matchup must be an integer")

            if min_responses_per_matchup < 3:
                raise ValueError("Min responses per matchup must be at least 3")

            logger.info(
                "Creating leaderboard %s with instruction %s, show_prompt %s, show_prompt_asset %s, inverse_ranking %s, level_of_detail %s, min_responses_per_matchup %s, validation_set_id %s, filters %s, settings %s",
                name,
                instruction,
                show_prompt,
                show_prompt_asset,
                inverse_ranking,
                level_of_detail,
                min_responses_per_matchup,
                validation_set_id,
                filters,
                settings,
            )

            leaderboard_result = self._openapi_service.leaderboard_api.leaderboard_post(
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

            logger.info("Leaderboard created with id %s", leaderboard_result.id)

            return RapidataLeaderboard(
                name,
                instruction,
                show_prompt,
                show_prompt_asset,
                inverse_ranking,
                leaderboard_result.response_budget,
                min_responses_per_matchup,
                self.id,
                leaderboard_result.id,
                self._openapi_service,
            )

    def evaluate_model(
        self,
        name: str,
        media: list[str],
        identifiers: list[str] | None = None,
        prompts: list[str] | None = None,
    ) -> None:
        """
        Evaluates a model on the benchmark across all leaderboards.

        prompts or identifiers must be provided to match the media.

        Args:
            name: The name of the model.
            media: The generated images/videos that will be used to evaluate the model.
            identifiers: The identifiers that correspond to the media. The order of the identifiers must match the order of the media.\n
                The identifiers that are used must be registered for the benchmark. To see the registered identifiers, use the identifiers property.
            prompts: The prompts that correspond to the media. The order of the prompts must match the order of the media.
        """
        with tracer.start_as_current_span("evaluate_model"):
            if not media:
                raise ValueError("Media must be a non-empty list of strings")

            if not identifiers and not prompts:
                raise ValueError("Identifiers or prompts must be provided.")

            if identifiers and prompts:
                raise ValueError(
                    "Identifiers and prompts cannot be provided at the same time. Use one or the other."
                )

            if not identifiers:
                assert prompts is not None
                identifiers = prompts

            if len(media) != len(identifiers):
                raise ValueError(
                    "Media and identifiers/prompts must have the same length"
                )

            if not all(identifier in self.identifiers for identifier in identifiers):
                raise ValueError(
                    "All identifiers/prompts must be in the registered identifiers/prompts list. To see the registered identifiers/prompts, use the identifiers/prompts property."
                )

            participant_result = self._openapi_service.benchmark_api.benchmark_benchmark_id_participants_post(
                benchmark_id=self.id,
                create_benchmark_participant_model=CreateBenchmarkParticipantModel(
                    name=name,
                ),
            )

            logger.info(f"Participant created: {participant_result.participant_id}")

            participant = BenchmarkParticipant(
                name, participant_result.participant_id, self._openapi_service
            )

            with tracer.start_as_current_span("upload_media_for_participant"):
                logger.info(
                    f"Uploading {len(media)} media assets to participant {participant.id}"
                )

                successful_uploads, failed_uploads = participant.upload_media(
                    media,
                    identifiers,
                )

                total_uploads = len(media)
                success_rate = (
                    (len(successful_uploads) / total_uploads * 100)
                    if total_uploads > 0
                    else 0
                )
                logger.info(
                    f"Upload complete: {len(successful_uploads)} successful, {len(failed_uploads)} failed ({success_rate:.1f}% success rate)"
                )

                if failed_uploads:
                    logger.error(f"Failed uploads for media: {failed_uploads}")
                    logger.warning(
                        "Some uploads failed. The model evaluation may be incomplete."
                    )

                if len(successful_uploads) == 0:
                    raise RuntimeError(
                        "No uploads were successful. The model evaluation will not be completed."
                    )

                self._openapi_service.participant_api.participants_participant_id_submit_post(
                    participant_id=participant_result.participant_id
                )

    def view(self) -> None:
        """
        Views the benchmark.
        """
        logger.info("Opening benchmark page in browser...")
        could_open_browser = webbrowser.open(self.__benchmark_page)
        if not could_open_browser:
            encoded_url = urllib.parse.quote(
                self.__benchmark_page, safe="%/:=&?~#+!$,;'@()*[]"
            )
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )

    def get_overall_standings(self, tags: Optional[list[str]] = None) -> pd.DataFrame:
        """
        Returns an aggregated elo table of all leaderboards in the benchmark.
        """
        with tracer.start_as_current_span("get_overall_standings"):
            participants = self._openapi_service.benchmark_api.benchmark_benchmark_id_standings_get(
                benchmark_id=self.id,
                tags=tags,
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

    def __str__(self) -> str:
        return f"RapidataBenchmark(name={self.name}, id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
