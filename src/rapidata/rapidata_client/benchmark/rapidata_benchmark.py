from __future__ import annotations
import os.path
import re
import urllib.parse
import webbrowser
from colorama import Fore
from typing import Literal, Optional, Sequence, TYPE_CHECKING, cast
from rapidata.rapidata_client.config import logger, managed_print, tracer
from rapidata.rapidata_client.benchmark._detail_mapper import LevelOfDetail
from rapidata.rapidata_client.benchmark._prompt_uploader import (
    BenchmarkPrompt,
    BenchmarkPromptUploader,
)
from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
    AudienceAudienceIdJobsGetJobIdParameter,
)
from rapidata.api_client.models.benchmark_demographic_dimension import (
    BenchmarkDemographicDimension,
)

if TYPE_CHECKING:
    import pandas as pd
    from rapidata.rapidata_client.audience._audience_base import RapidataAudienceBase
    from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
        RapidataLeaderboard,
    )
    from rapidata.rapidata_client.benchmark.participant.participant import (
        BenchmarkParticipant,
    )
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
        self.__english_prompts: list[str | None] = []
        self.__prompt_assets: list[str | None] = []
        self.__leaderboards: list["RapidataLeaderboard"] = []
        self.__identifiers: list[str] = []
        self.__tags: list[list[str]] = []
        self.__participants: list[BenchmarkParticipant] = []
        self.__benchmark_page: str = (
            f"https://app.{self._openapi_service.environment}/mri/benchmarks/{self.id}"
        )
        self._prompt_uploader = BenchmarkPromptUploader(id, openapi_service)

    def __instantiate_prompts(self) -> None:
        from rapidata.rapidata_client.config import tracer
        from rapidata.api_client.models.i_asset_model_file_asset_model import (
            IAssetModelFileAssetModel,
        )
        from rapidata.api_client.models.i_metadata_model_source_url_metadata_model import (
            IMetadataModelSourceUrlMetadataModel,
        )
        from rapidata.api_client.models.i_metadata_model_original_filename_metadata_model import (
            IMetadataModelOriginalFilenameMetadataModel,
        )

        with tracer.start_as_current_span("RapidataBenchmark.__instantiate_prompts"):
            self.__prompts = []
            self.__english_prompts = []
            self.__identifiers = []
            self.__prompt_assets = []
            self.__tags = []

            current_page = 1
            total_pages = None

            while True:
                prompts_result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_prompts_get(
                    benchmark_id=self.id,
                    page=current_page,
                    page_size=100,
                )

                if prompts_result.total_pages is None:
                    raise ValueError(
                        "An error occurred while fetching prompts: total_pages is None"
                    )

                total_pages = prompts_result.total_pages

                for prompt in prompts_result.items:
                    self.__prompts.append(prompt.original_prompt)
                    self.__english_prompts.append(prompt.english_prompt)
                    self.__identifiers.append(prompt.identifier)
                    if prompt.prompt_asset is None:
                        self.__prompt_assets.append(None)
                    else:
                        file_asset = prompt.prompt_asset.actual_instance
                        assert isinstance(file_asset, IAssetModelFileAssetModel)
                        source_url = file_asset.metadata.get("sourceUrl")
                        original_filename = file_asset.metadata.get("originalFilename")
                        if source_url is not None:
                            instance = source_url.actual_instance
                            assert isinstance(
                                instance, IMetadataModelSourceUrlMetadataModel
                            )
                            self.__prompt_assets.append(instance.url)
                        elif original_filename is not None:
                            instance = original_filename.actual_instance
                            assert isinstance(
                                instance, IMetadataModelOriginalFilenameMetadataModel
                            )
                            self.__prompt_assets.append(instance.original_filename)
                        else:
                            self.__prompt_assets.append(None)

                    self.__tags.append(prompt.tags)
                if current_page >= total_pages:
                    break

                current_page += 1

    # http / https in any case — same detection the asset uploader uses to tell
    # a remote URL from a local path.
    __URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)

    @classmethod
    def __normalize_cached_asset(cls, asset: str | None) -> str | None:
        """Mirror the representation a re-fetch would reconstruct for an asset.

        `__instantiate_prompts` rebuilds assets from server metadata: remote
        URLs come back verbatim (`sourceUrl`), but local files come back as just
        their base filename (`originalFilename`). Normalizing the freshly
        uploaded value here keeps `prompt_assets` identical before and after any
        re-fetch, so it stays idempotent as input to downstream calls.
        """
        if asset is None or cls.__URL_SCHEME_RE.match(asset):
            return asset

        return os.path.basename(asset)

    @property
    def identifiers(self) -> list[str]:
        if not self.__identifiers:
            self.__instantiate_prompts()

        return self.__identifiers

    @property
    def prompts(self) -> list[str | None]:
        """
        Returns the prompts as originally provided, in the order they were registered.
        """
        if not self.__prompts:
            self.__instantiate_prompts()

        return self.__prompts

    @property
    def english_prompts(self) -> list[str | None]:
        """
        Returns the prompts translated to English, aligned by index with `prompts`.

        The translations are produced server-side, so accessing this after
        `add_prompts` triggers a one-off re-fetch of the prompt set.
        """
        if not self.__english_prompts:
            self.__instantiate_prompts()

        return self.__english_prompts

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
        from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
            RapidataLeaderboard,
        )

        with tracer.start_as_current_span("RapidataBenchmark.leaderboards"):
            if not self.__leaderboards:
                current_page = 1
                total_pages = None

                while True:
                    leaderboards_result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_leaderboards_get(
                        benchmark_id=self.id,
                        page=current_page,
                        page_size=100,
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

    @property
    def participants(self) -> list[BenchmarkParticipant]:
        """Returns the participants that are registered for the benchmark."""
        from rapidata.rapidata_client.benchmark.participant.participant import (
            BenchmarkParticipant,
        )

        with tracer.start_as_current_span("RapidataBenchmark.participants"):
            if not self.__participants:
                result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_participants_get(
                    benchmark_id=self.id,
                )

                self.__participants = [
                    BenchmarkParticipant(
                        name=p.name,
                        id=p.id,
                        openapi_service=self._openapi_service,
                        benchmark_id=self.id,
                        status=p.status,
                    )
                    for p in result.items
                ]

            return self.__participants

    def add_prompts(
        self,
        identifiers: Optional[list[str]] = None,
        prompts: Optional[list[str | None] | list[str]] = None,
        prompt_assets: Optional[list[str | None] | list[str]] = None,
        tags: Optional[list[list[str] | None] | list[list[str]]] = None,
    ) -> None:
        """
        Adds one or more prompts to the benchmark. Everything is matched up by the
        indexes of the lists.

        prompts or identifiers must be provided, as well as prompts or prompt_assets.

        The prompts are uploaded concurrently. A failed upload does not abort the
        rest: every prompt is attempted, failures are logged, and only the prompts
        that succeeded are registered.

        Args:
            identifiers: The identifiers of the prompts/assets/tags that will be used to match up the media. If not provided, it will use the prompts as the identifiers.
            prompts: The prompts that will be registered for the benchmark.
            prompt_assets: The prompt assets that will be registered for the benchmark.
            tags: The tags that will be associated with the prompts to use for filtering the leaderboard results. They will NOT be shown to the users.

        Example:
            ```python
            benchmark.add_prompts(
                identifiers=["id1", "id2"],
                prompts=["prompt 1", "prompt 2"],
                prompt_assets=["https://assets.rapidata.ai/prompt_1.jpg", "https://assets.rapidata.ai/prompt_2.jpg"],
                tags=[["tag1", "tag2"], ["tag2"]],
            )
            ```
        """
        with tracer.start_as_current_span("RapidataBenchmark.add_prompts"):
            if prompts and (
                not isinstance(prompts, list)
                or not all(
                    isinstance(prompt, str) or prompt is None for prompt in prompts
                )
            ):
                raise ValueError("Prompts must be a list of strings or None.")

            if prompt_assets and (
                not isinstance(prompt_assets, list)
                or not all(
                    isinstance(asset, str) or asset is None for asset in prompt_assets
                )
            ):
                raise ValueError("Media assets must be a list of strings or None.")

            if identifiers and (
                not isinstance(identifiers, list)
                or not all(isinstance(identifier, str) for identifier in identifiers)
            ):
                raise ValueError("Identifiers must be a list of strings.")

            if identifiers and len(set(identifiers)) != len(identifiers):
                raise ValueError("Identifiers must be unique.")

            if tags is not None:
                if not isinstance(tags, list):
                    raise ValueError("Tags must be a list of lists of strings or None.")

                for tag in tags:
                    if tag is not None and (
                        not isinstance(tag, list)
                        or not all(isinstance(item, str) for item in tag)
                    ):
                        raise ValueError(
                            "Tags must be a list of lists of strings or None."
                        )

            if not identifiers and not prompts:
                raise ValueError(
                    "At least one of identifiers or prompts must be provided."
                )

            if not prompts and not prompt_assets:
                raise ValueError(
                    "At least one of prompts or media assets must be provided."
                )

            if not identifiers:
                assert prompts is not None
                if len(set(prompts)) != len(prompts):
                    raise ValueError(
                        "Prompts must be unique. Otherwise use identifiers."
                    )
                if any(prompt is None for prompt in prompts):
                    raise ValueError(
                        "Prompts must not be None. Otherwise use identifiers."
                    )

                identifiers = cast(list[str], prompts)

            assert identifiers is not None

            expected_length = len(identifiers)

            if not prompts:
                prompts = cast(list[str | None], [None] * expected_length)

            if not prompt_assets:
                prompt_assets = cast(list[str | None], [None] * expected_length)

            if not tags:
                tags = cast(list[list[str] | None], [None] * expected_length)

            if not (expected_length == len(prompts) == len(prompt_assets) == len(tags)):
                raise ValueError(
                    "Identifiers, prompts, media assets, and tags must have the same length or set to None."
                )

            # Snapshot once: `self.identifiers` is a property whose getter re-fetches
            # over HTTP while the cache is empty, so testing it inside the comprehension
            # fired one request per identifier (a full re-fetch each time on a fresh,
            # empty benchmark). One lookup into a set instead.
            existing_identifiers = set(self.identifiers)
            already_registered = [
                identifier
                for identifier in identifiers
                if identifier in existing_identifiers
            ]
            if already_registered:
                raise ValueError(
                    f"Identifiers already exist in the benchmark: {already_registered}"
                )

            to_upload = [
                BenchmarkPrompt(
                    identifier, prompt, asset, tag if tag is not None else []
                )
                for identifier, prompt, asset, tag in zip(
                    identifiers, prompts, prompt_assets, tags
                )
            ]

            for uploaded in self._prompt_uploader.upload_many(to_upload):
                self.__identifiers.append(uploaded.identifier)
                self.__prompts.append(uploaded.prompt)
                self.__prompt_assets.append(
                    self.__normalize_cached_asset(uploaded.prompt_asset)
                )
                self.__tags.append(uploaded.tags)

            # The English translation is produced server-side and is unknown for
            # the just-added prompts. Clear it so the next access lazily re-fetches
            # the prompt set, while the rest of the cache stays intact.
            self.__english_prompts = []

    def create_leaderboard(
        self,
        name: str,
        instruction: str,
        show_prompt: bool = False,
        show_prompt_asset: bool = False,
        inverse_ranking: bool = False,
        level_of_detail: LevelOfDetail | int | None = None,
        min_responses_per_matchup: int | None = None,
        audience_id: str | RapidataAudienceBase | None = None,
        settings: Sequence["RapidataSetting"] | None = None,
    ) -> RapidataLeaderboard:
        """
        Creates a new leaderboard for the benchmark.

        Args:
            name: The name of the leaderboard. (not shown to the users)
            instruction: The instruction decides how the models will be evaluated.
            show_prompt: Whether to show the prompt to the users. (default: False)
            show_prompt_asset: Whether to show the prompt asset to the users. (only works if the prompt asset is a URL) (default: False)
            inverse_ranking: Whether to inverse the ranking of the leaderboard. (if the question is inversed, e.g. "Which video is worse?")
            level_of_detail: Sets the leaderboard's response budget — the total number of comparison responses collected per model evaluation. A larger budget buys more matchups and therefore more precise standings, at the cost of a slower, more expensive evaluation. Either one of the named levels — 'debug' (20 responses), 'low' (2,000), 'medium' (4,000), 'high' (8,000), 'very high' (16,000) — or a positive integer for a custom budget. (default: None, server decides)
            min_responses_per_matchup: The minimum number of responses required to be considered for the leaderboard. (default: 3)
            audience_id: The audience that should answer the leaderboard. Pass either the audience id, a :class:`RapidataAudience` (dimension audience), or a :class:`RapidataFilteredAudience` (derived via :py:meth:`RapidataAudience.filter`). Defaults to the global audience when not specified.
            settings: The settings that should be applied to the leaderboard. Will determine the behavior of the tasks on the leaderboard. (default: [])
        """
        from rapidata.api_client.models.create_leaderboard_endpoint_input import (
            CreateLeaderboardEndpointInput,
        )
        from rapidata.rapidata_client.audience._audience_base import (
            RapidataAudienceBase,
        )
        from rapidata.rapidata_client.benchmark._detail_mapper import DetailMapper
        from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import (
            RapidataLeaderboard,
        )

        with tracer.start_as_current_span("RapidataBenchmark.create_leaderboard"):
            response_budget = (
                DetailMapper.resolve_budget(level_of_detail)
                if level_of_detail is not None
                else None
            )

            if min_responses_per_matchup is not None and (
                not isinstance(min_responses_per_matchup, int)
                or min_responses_per_matchup < 3
            ):
                raise ValueError(
                    "Min responses per matchup must be an integer and at least 3"
                )

            resolved_audience_id = (
                audience_id.id
                if isinstance(audience_id, RapidataAudienceBase)
                else audience_id
            )

            logger.info(
                "Creating leaderboard %s with instruction %s, show_prompt %s, show_prompt_asset %s, inverse_ranking %s, level_of_detail %s, min_responses_per_matchup %s, audience_id %s, settings %s",
                name,
                instruction,
                show_prompt,
                show_prompt_asset,
                inverse_ranking,
                level_of_detail,
                min_responses_per_matchup,
                resolved_audience_id,
                settings,
            )

            leaderboard_result = (
                self._openapi_service.leaderboard.leaderboard_api.leaderboard_post(
                    create_leaderboard_endpoint_input=CreateLeaderboardEndpointInput(
                        benchmarkId=self.id,
                        name=name,
                        instruction=instruction,
                        showPrompt=show_prompt,
                        showPromptAsset=show_prompt_asset,
                        isInversed=inverse_ranking,
                        minResponses=min_responses_per_matchup,
                        responseBudget=response_budget,
                        audienceId=resolved_audience_id,
                        featureFlags=(
                            [setting._to_feature_flag() for setting in settings]
                            if settings
                            else None
                        ),
                    )
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
                leaderboard_result.min_responses,
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
        data_type: Literal["media", "text"] = "media",
    ) -> None:
        """
        Evaluates a model on the benchmark across all leaderboards.

        prompts or identifiers must be provided to match the media.

        Args:
            name: The name of the model.
            media: The generated media or text that will be used to evaluate the model.
            identifiers: The identifiers that correspond to the media. The order of the identifiers must match the order of the media.\n
                The identifiers that are used must be registered for the benchmark. To see the registered identifiers, use the identifiers property.
            prompts: The prompts that correspond to the media. The order of the prompts must match the order of the media.
            data_type: The type of data being provided. Use "media" for images/videos/audio (default) or "text" for text content.
        """
        with tracer.start_as_current_span("RapidataBenchmark.evaluate_model"):
            participant = self.add_model(
                name=name,
                media=media,
                identifiers=identifiers,
                prompts=prompts,
                data_type=data_type,
            )
            participant.run()

    def add_model(
        self,
        name: str,
        media: list[str],
        identifiers: list[str] | None = None,
        prompts: list[str] | None = None,
        data_type: Literal["media", "text"] = "media",
    ) -> BenchmarkParticipant:
        """Adds a model to the benchmark without immediately submitting it for evaluation.

        This method creates a participant, uploads media, but does NOT submit the participant.
        Use `participant.run()` or `benchmark.run()` to submit afterwards.

        Args:
            name: The name of the model.
            media: The generated media or text that will be used to evaluate the model.
            identifiers: The identifiers that correspond to the media. The order of the identifiers must match the order of the media.\n
                The identifiers that are used must be registered for the benchmark. To see the registered identifiers, use the identifiers property.
            prompts: The prompts that correspond to the media. The order of the prompts must match the order of the media.
            data_type: The type of data being provided. Use "media" for images/videos/audio (default) or "text" for text content.

        Returns:
            The created BenchmarkParticipant instance.
        """
        from rapidata.api_client.models.create_benchmark_participant_endpoint_input import (
            CreateBenchmarkParticipantEndpointInput,
        )
        from rapidata.rapidata_client.benchmark.participant.participant import (
            BenchmarkParticipant,
        )

        with tracer.start_as_current_span("RapidataBenchmark.add_model"):
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

            participant_result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_participants_post(
                benchmark_id=self.id,
                create_benchmark_participant_endpoint_input=CreateBenchmarkParticipantEndpointInput(
                    name=name,
                ),
            )

            logger.info(f"Participant created: {participant_result.participant_id}")

            participant = BenchmarkParticipant(
                name,
                participant_result.participant_id,
                self._openapi_service,
                self.id,
            )

            with tracer.start_as_current_span("upload_media_for_participant"):
                logger.info(
                    f"Uploading {len(media)} media assets to participant {participant.id}"
                )

                successful_uploads, failed_uploads = participant.upload_media(
                    media,
                    identifiers,
                    data_type=data_type,
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

            # Clear cache so next access re-fetches
            self.__participants = []

            return participant

    def run(self) -> None:
        """Submits all participants that are in `CREATED` state.

        This is a convenience method to submit all unsubmitted participants at once.
        """
        from rapidata.api_client.models.participant_status import ParticipantStatus

        with tracer.start_as_current_span("RapidataBenchmark.run"):
            created = [
                p for p in self.participants if p.status == ParticipantStatus.CREATED
            ]
            logger.info(f"Submitting {len(created)} participants in CREATED state")
            for participant in created:
                participant.run()

            # Clear cache so next access re-fetches
            self.__participants = []

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

    def get_overall_standings(
        self,
        tags: Optional[list[str]] = None,
        leaderboard_ids: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """
        Returns an aggregated elo table of all leaderboards in the benchmark.

        Args:
            tags: Filter standings by these tags. If None, all tags are considered.
            leaderboard_ids: Filter to only include matchups from these leaderboards. If None, all leaderboards are considered.
        """
        import pandas as pd

        with tracer.start_as_current_span("get_overall_standings"):
            tags_filter = AudienceAudienceIdJobsGetJobIdParameter()
            tags_filter.var_in = tags
            leaderboard_filter = AudienceAudienceIdJobsGetJobIdParameter()
            leaderboard_filter.var_in = leaderboard_ids

            participants = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_standings_query_get(
                benchmark_id=self.id,
                tags=tags_filter,
                leaderboard_id=leaderboard_filter,
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

    def get_win_loss_matrix(
        self,
        tags: Optional[list[str]] = None,
        participant_ids: Optional[list[str]] = None,
        leaderboard_ids: Optional[list[str]] = None,
        use_weighted_scoring: Optional[bool] = None,
    ) -> pd.DataFrame:
        """
        Returns the pairwise win/loss matrix aggregated across the benchmark's leaderboards.

        The returned DataFrame is square, with participant names on both the index
        (rows) and columns. Cell ``[i, j]`` is how often participant ``i`` (row) beat
        participant ``j`` (column) in their direct matchups, summed over every
        leaderboard in scope. Read a row to see how a model did against every
        opponent; the diagonal (a model against itself) is always 0. This is the
        head-to-head breakdown behind :meth:`get_overall_standings`, which collapses
        the same matchups into a single Elo score per model.

        Args:
            tags: Only count matchups carrying one of these prompt tags. If None,
                every matchup is included; if an empty list, none are.
            participant_ids: Restrict the matrix to these participants. If None, all
                participants are included.
            leaderboard_ids: Only aggregate matchups from these leaderboards. If None,
                all leaderboards in the benchmark are included.
            use_weighted_scoring: If True, each matchup is weighted by the responding
                annotators' reliability (``userScore``) instead of being counted as a
                plain win, so cells hold weighted sums (floats) rather than raw counts.
                If False, cells are raw win counts. When None (default), the server
                applies its configured default.

        Returns:
            A pandas DataFrame indexed by participant name on both axes, where cell
            ``[i, j]`` holds the (optionally weighted) number of wins of the row
            participant over the column participant.
        """
        import pandas as pd

        with tracer.start_as_current_span("get_win_loss_matrix"):
            tags_filter = AudienceAudienceIdJobsGetJobIdParameter()
            tags_filter.var_in = tags
            participant_filter = AudienceAudienceIdJobsGetJobIdParameter()
            participant_filter.var_in = participant_ids
            leaderboard_filter = AudienceAudienceIdJobsGetJobIdParameter()
            leaderboard_filter.var_in = leaderboard_ids

            result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_matrix_query_get(
                benchmark_id=self.id,
                tags=tags_filter,
                participant_id=participant_filter,
                leaderboard_id=leaderboard_filter,
                use_weighted_scoring=use_weighted_scoring,
            )

            return pd.DataFrame(
                data=result.data,
                index=pd.Index(result.index),
                columns=pd.Index(result.columns),
            )

    def get_demographics(
        self,
        tags: Optional[list[str]] = None,
        leaderboard_ids: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Returns the demographic composition of the voters for this benchmark.

        One row per (dimension, bucket): the ``votes`` cast by that bucket and
        its ``share`` of the dimension's votes (a dimension's shares sum to 1).
        Every dimension (``ageBucket``, ``gender``, ``occupation``, ``country``,
        ``language``) includes an ``"unknown"`` bucket for votes whose attribute
        could not be determined.

        ``ageBucket``, ``gender`` and ``occupation`` are estimated (inferred from
        behaviour), not self-declared; ``country`` and ``language`` are observed.

        Args:
            tags: Only count votes on matchups with these tags. If None, all matchups are considered.
            leaderboard_ids: Only count votes from these leaderboards. If None, all leaderboards are considered.
            run_id: Only count votes from this evaluation run. If None, all runs are considered.

        Returns:
            A pandas DataFrame with columns ``dimension``, ``value``, ``votes``, ``share``.
        """
        import pandas as pd

        with tracer.start_as_current_span("RapidataBenchmark.get_demographics"):
            tags_filter, leaderboard_filter, run_filter = self.__demographic_filters(
                tags, leaderboard_ids, run_id
            )
            result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_demographics_get(
                benchmark_id=self.id,
                tags=tags_filter,
                leaderboard_id=leaderboard_filter,
                run_id=run_filter,
            )

            dimensions = result.dimensions
            dimension_buckets = {
                "ageBucket": dimensions.age_bucket,
                "gender": dimensions.gender,
                "occupation": dimensions.occupation,
                "country": dimensions.country,
                "language": dimensions.language,
            }
            rows = [
                {
                    "dimension": name,
                    "value": bucket.value,
                    "votes": bucket.votes,
                    "share": bucket.share,
                }
                for name, buckets in dimension_buckets.items()
                for bucket in buckets
            ]

            return pd.DataFrame(
                rows, columns=pd.Index(["dimension", "value", "votes", "share"])
            )

    def get_standings_breakdown(
        self,
        dimension: BenchmarkDemographicDimension,
        tags: Optional[list[str]] = None,
        leaderboard_ids: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Returns the standings split by a demographic dimension of the voters.

        One row per (segment, model): how each demographic segment of voters
        ranks the models, alongside that segment's vote count. The segments
        include an ``"unknown"`` bucket. Scores are raw vote counts. For the
        overall standings across all voters, use :py:meth:`get_overall_standings`.

        ``AgeBucket``, ``Gender`` and ``Occupation`` are estimated (inferred), not
        self-declared; ``Country`` and ``Language`` are observed.

        Args:
            dimension: The :class:`BenchmarkDemographicDimension` to split by (``AgeBucket``, ``Gender``, ``Occupation``, ``Country`` or ``Language``).
            tags: Only count votes on matchups with these tags. If None, all matchups are considered.
            leaderboard_ids: Only count votes from these leaderboards. If None, all leaderboards are considered.
            run_id: Only count votes from this evaluation run. If None, all runs are considered.

        Returns:
            A pandas DataFrame with columns ``segment``, ``segment_votes``, ``name``, ``wins``, ``total_matches``, ``score``.
        """
        import pandas as pd

        with tracer.start_as_current_span("RapidataBenchmark.get_standings_breakdown"):
            tags_filter, leaderboard_filter, run_filter = self.__demographic_filters(
                tags, leaderboard_ids, run_id
            )
            result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_standings_breakdown_get(
                benchmark_id=self.id,
                dimension=BenchmarkDemographicDimension(dimension),
                tags=tags_filter,
                leaderboard_id=leaderboard_filter,
                run_id=run_filter,
            )

            rows = []
            for segment in result.segments:
                for item in segment.items:
                    rows.append(
                        {
                            "segment": segment.value,
                            "segment_votes": segment.votes,
                            "name": item.name,
                            "wins": item.wins,
                            "total_matches": item.total_matches,
                            "score": (
                                round(item.score, 2) if item.score is not None else None
                            ),
                        }
                    )

            return pd.DataFrame(
                rows,
                columns=pd.Index(
                    [
                        "segment",
                        "segment_votes",
                        "name",
                        "wins",
                        "total_matches",
                        "score",
                    ]
                ),
            )

    def __demographic_filters(
        self,
        tags: Optional[list[str]],
        leaderboard_ids: Optional[list[str]],
        run_id: Optional[str],
    ) -> tuple[
        AudienceAudienceIdJobsGetJobIdParameter,
        AudienceAudienceIdJobsGetJobIdParameter,
        AudienceAudienceIdJobsGetJobIdParameter,
    ]:
        tags_filter = AudienceAudienceIdJobsGetJobIdParameter()
        tags_filter.var_in = tags
        leaderboard_filter = AudienceAudienceIdJobsGetJobIdParameter()
        leaderboard_filter.var_in = leaderboard_ids
        run_filter = AudienceAudienceIdJobsGetJobIdParameter()
        run_filter.var_in = [run_id] if run_id is not None else None
        return tags_filter, leaderboard_filter, run_filter

    def __str__(self) -> str:
        return f"RapidataBenchmark(name={self.name}, id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
