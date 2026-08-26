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
from rapidata.api_client.models.benchmark_demographic_dimension import (
    BenchmarkDemographicDimension,
)
from rapidata.rapidata_client.benchmark._vote_filters import (
    demographic_filters,
    in_filter,
)
from rapidata.rapidata_client.benchmark.leaderboard.vote_aggregation import (
    VoteAggregation,
)
from rapidata.rapidata_client.benchmark.prompt_metadata import (
    BenchmarkPromptInfo,
    Origin,
    Tag,
    coerce_origin,
    coerce_tags,
    is_tag_list,
)
from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
    AudienceAudienceIdJobsGetJobIdParameter,
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
    from rapidata.rapidata_client.filter.models.gender import Gender
    from rapidata.rapidata_client.filter.models.age_group import AgeGroup
    from rapidata.api_client.models.get_prompts_by_benchmark_endpoint_output import (
        GetPromptsByBenchmarkEndpointOutput,
    )
    from rapidata.rapidata_client.settings import RapidataSetting
    from rapidata.service.openapi_service import OpenAPIService


# A batch-wide failure would otherwise print one full error block per sample.
_MAX_REPORTED_FAILURES = 5

# The submit endpoint accepts at most 100 participant ids per request and
# rejects anything larger outright, so submissions are chunked to this size.
_SUBMIT_BATCH_SIZE = 100


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
        self.__structured_tags: list[list[Tag]] = []
        self.__origins: list[Origin | None] = []
        self.__prompt_ids: dict[str, str] = {}
        self.__participants: list[BenchmarkParticipant] = []
        self.__benchmark_page: str = (
            f"https://app.{self._openapi_service.environment}/mri/benchmarks/{self.id}"
        )
        self._prompt_uploader = BenchmarkPromptUploader(id, openapi_service)

    @staticmethod
    def __extract_asset_url(prompt: GetPromptsByBenchmarkEndpointOutput) -> str | None:
        """Reconstruct a prompt's asset reference from the server metadata.

        Remote assets come back as their `sourceUrl`; locally-uploaded ones as
        the bare `originalFilename`.
        """
        from rapidata.api_client.models.i_asset_model_file_asset_model import (
            IAssetModelFileAssetModel,
        )
        from rapidata.api_client.models.i_metadata_model_source_url_metadata_model import (
            IMetadataModelSourceUrlMetadataModel,
        )
        from rapidata.api_client.models.i_metadata_model_original_filename_metadata_model import (
            IMetadataModelOriginalFilenameMetadataModel,
        )

        if prompt.prompt_asset is None:
            return None
        file_asset = prompt.prompt_asset.actual_instance
        assert isinstance(file_asset, IAssetModelFileAssetModel)
        source_url = file_asset.metadata.get("sourceUrl")
        original_filename = file_asset.metadata.get("originalFilename")
        if source_url is not None:
            instance = source_url.actual_instance
            assert isinstance(instance, IMetadataModelSourceUrlMetadataModel)
            return instance.url
        if original_filename is not None:
            instance = original_filename.actual_instance
            assert isinstance(instance, IMetadataModelOriginalFilenameMetadataModel)
            return instance.original_filename
        return None

    @classmethod
    def __to_prompt_info(
        cls, prompt: GetPromptsByBenchmarkEndpointOutput
    ) -> BenchmarkPromptInfo:
        """Map a generated prompt output model to the user-facing info object."""
        return BenchmarkPromptInfo(
            identifier=prompt.identifier,
            prompt=prompt.original_prompt,
            english_prompt=prompt.english_prompt,
            prompt_asset=cls.__extract_asset_url(prompt),
            tags=[Tag(value=tag.value, category=tag.category) for tag in prompt.tags],
            origin=(
                Origin(source=prompt.origin.source)
                if prompt.origin is not None
                else None
            ),
        )

    def __instantiate_prompts(self) -> None:
        from rapidata.rapidata_client.config import tracer

        with tracer.start_as_current_span("RapidataBenchmark.__instantiate_prompts"):
            self.__prompts = []
            self.__english_prompts = []
            self.__identifiers = []
            self.__prompt_assets = []
            self.__tags = []
            self.__structured_tags = []
            self.__origins = []
            self.__prompt_ids = {}

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
                    info = self.__to_prompt_info(prompt)
                    self.__prompts.append(info.prompt)
                    self.__english_prompts.append(info.english_prompt)
                    self.__identifiers.append(info.identifier)
                    self.__prompt_assets.append(info.prompt_asset)
                    self.__structured_tags.append(info.tags)
                    self.__tags.append([tag.value for tag in info.tags])
                    self.__origins.append(info.origin)
                    self.__prompt_ids[prompt.identifier] = prompt.id
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
        Returns the tag values registered for the benchmark, aligned by index with `prompts`.

        This is the flat, values-only view of the tags. It is kept for
        backwards compatibility — prefer `structured_tags` for the
        (value + category) representation.
        """
        if not self.__tags:
            self.__instantiate_prompts()

        return self.__tags

    @property
    def structured_tags(self) -> list[list[Tag]]:
        """
        Returns the structured tags registered for the benchmark, aligned by index with `prompts`.

        Each :class:`Tag` carries a ``value`` and an optional ``category``. Tags
        are used to filter and organize leaderboard results and are NOT shown to
        the annotators.
        """
        if not self.__structured_tags:
            self.__instantiate_prompts()

        return self.__structured_tags

    @property
    def origins(self) -> list[Origin | None]:
        """
        Returns the origin of each prompt, aligned by index with `prompts`.

        A prompt without an origin is represented as ``None``.
        """
        if not self.__origins:
            self.__instantiate_prompts()

        return self.__origins

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
                                leaderboard.included_tags,
                                leaderboard.excluded_tags,
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
        tags: Optional[Sequence[Sequence[str | Tag] | None]] = None,
        origins: Optional[Sequence[Origin | str | None]] = None,
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
            tags: The tags per prompt, used to filter and organize the leaderboard results. They are NOT shown to the users. Each entry is a list of plain strings, a list of :class:`Tag` (a `value` plus an optional `category`), or a mix of both — strings are converted to `Tag(value, category=None)` internally. None means no tags for that prompt.
            origins: The origin of each prompt (e.g. a source dataset). Each entry is a plain string (converted to `Origin(source)`), an :class:`Origin`, or None.

        Example:
            ```python
            # Plain strings are all you need when you don't want categories.
            benchmark.add_prompts(
                identifiers=["id1", "id2"],
                prompts=["prompt 1", "prompt 2"],
                prompt_assets=["https://assets.rapidata.ai/prompt_1.jpg", "https://assets.rapidata.ai/prompt_2.jpg"],
                tags=[["landscape", "outdoor"], ["portrait"]],
                origins=["coco", "coco"],
            )

            # Reach for Tag only where you want to group tags by category.
            from rapidata import Tag

            benchmark.add_prompts(
                identifiers=["id3"],
                prompts=["prompt 3"],
                tags=[[Tag("landscape", category="scene"), "outdoor"]],
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
                if not is_tag_list(tags):
                    raise ValueError("Tags must be a list of lists of str/Tag or None.")

                for tag in tags:
                    if tag is not None and (
                        not is_tag_list(tag)
                        or not all(isinstance(item, (str, Tag)) for item in tag)
                    ):
                        raise ValueError(
                            "Tags must be a list of lists of str/Tag or None."
                        )

            if origins is not None:
                if not is_tag_list(origins) or not all(
                    origin is None or isinstance(origin, (Origin, str))
                    for origin in origins
                ):
                    raise ValueError("Origins must be a list of Origin/str or None.")

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
                tags = cast(
                    Sequence[Sequence[str | Tag] | None], [None] * expected_length
                )

            if not origins:
                origins = cast(Sequence[Origin | str | None], [None] * expected_length)

            if not (
                expected_length
                == len(prompts)
                == len(prompt_assets)
                == len(tags)
                == len(origins)
            ):
                raise ValueError(
                    "Identifiers, prompts, media assets, tags, and origins must have the same length or set to None."
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
                    identifier,
                    prompt,
                    asset,
                    coerce_tags(tag),
                    coerce_origin(origin),
                )
                for identifier, prompt, asset, tag, origin in zip(
                    identifiers, prompts, prompt_assets, tags, origins
                )
            ]

            for uploaded in self._prompt_uploader.upload_many(to_upload):
                self.__identifiers.append(uploaded.identifier)
                self.__prompts.append(uploaded.prompt)
                self.__prompt_assets.append(
                    self.__normalize_cached_asset(uploaded.prompt_asset)
                )
                self.__structured_tags.append(uploaded.tags)
                self.__tags.append([tag.value for tag in uploaded.tags])
                self.__origins.append(uploaded.origin)

            # The English translation is produced server-side and is unknown for
            # the just-added prompts. Clear it so the next access lazily re-fetches
            # the prompt set, while the rest of the cache stays intact.
            self.__english_prompts = []

    def update_prompt(
        self,
        identifier: str,
        tags: Optional[Sequence[str | Tag]] = None,
        origin: Origin | str | None = None,
    ) -> None:
        """Updates the tags and/or origin of an existing prompt.

        Only the provided fields are changed: pass ``tags`` to replace the
        prompt's tags, ``origin`` to set its origin, or both. A field left as
        ``None`` is not sent and the server leaves it unchanged.

        Args:
            identifier: The identifier of the prompt to update. Must already be registered on the benchmark.
            tags: The new tags for the prompt — plain strings, :class:`Tag` objects, or a mix; strings are converted to `Tag(value, category=None)`. Replaces the existing tags.
            origin: The new origin (an :class:`Origin` or a plain string mapped to `Origin(source)`).
        """
        from rapidata.api_client.models.update_prompt_tags_endpoint_input import (
            UpdatePromptTagsEndpointInput,
        )
        from rapidata.api_client.models.tag import Tag as ApiTag
        from rapidata.api_client.models.origin import Origin as ApiOrigin

        with tracer.start_as_current_span("RapidataBenchmark.update_prompt"):
            if tags is None and origin is None:
                raise ValueError("Provide tags and/or origin to update.")

            if tags is not None and (
                not is_tag_list(tags)
                or not all(isinstance(item, (str, Tag)) for item in tags)
            ):
                raise ValueError("Tags must be a list of str/Tag.")

            if origin is not None and not isinstance(origin, (Origin, str)):
                raise ValueError("Origin must be an Origin or str.")

            if identifier not in self.__prompt_ids:
                self.__instantiate_prompts()
            if identifier not in self.__prompt_ids:
                raise ValueError(
                    f"Identifier does not exist in the benchmark: {identifier}"
                )
            prompt_id = self.__prompt_ids[identifier]

            structured_tags = coerce_tags(tags) if tags is not None else None
            resolved_origin = coerce_origin(origin)

            self._openapi_service.leaderboard.prompt_api.benchmark_prompt_prompt_id_tags_put(
                prompt_id=prompt_id,
                update_prompt_tags_endpoint_input=UpdatePromptTagsEndpointInput(
                    tags=(
                        [
                            ApiTag(value=tag.value, category=tag.category)
                            for tag in structured_tags
                        ]
                        if structured_tags is not None
                        else None
                    ),
                    origin=(
                        ApiOrigin(source=resolved_origin.source)
                        if resolved_origin is not None
                        else None
                    ),
                ),
            )

            # Reflect the change in the caches so a subsequent read is consistent
            # without a re-fetch.
            if identifier in self.__identifiers:
                index = self.__identifiers.index(identifier)
                if structured_tags is not None:
                    self.__structured_tags[index] = structured_tags
                    self.__tags[index] = [tag.value for tag in structured_tags]
                if resolved_origin is not None:
                    self.__origins[index] = resolved_origin

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
        included_tags: list[str] | None = None,
        excluded_tags: list[str] | None = None,
        vote_aggregation: VoteAggregation = VoteAggregation.MAJORITY_VOTE,
        skip_initial_run: bool = False,
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
            included_tags: Restricts **which of the benchmark's prompts this leaderboard collects matchups for**: only prompts carrying at least one of these tag values are used. When empty or not specified (the default) every prompt is eligible. Note that a non-empty list drops untagged prompts. (default: None)
            excluded_tags: Prompt tag values to skip when collecting matchups. Always wins over ``included_tags`` — a prompt carrying both an included and an excluded tag is skipped. (default: None)
            vote_aggregation: How the responses on a single matchup are aggregated into that matchup's result. :attr:`VoteAggregation.MAJORITY_VOTE` (the default) collapses each matchup to one win for the majority side, ties split 0.5/0.5, so every matchup weighs the same no matter how many responses it collected. :attr:`VoteAggregation.ALL_VOTES` counts every individual response as its own matchup, which lets heavily-answered matchups dominate the standings. Changeable afterwards via :attr:`RapidataLeaderboard.vote_aggregation`.
            skip_initial_run: Whether to skip the initial run that evaluates the models already in the benchmark against each other. Adding a model afterwards still compares it against the whole existing field, and boosting the leaderboard still works — you just start with no responses collected and therefore no standings. Set this when you want to choose what gets evaluated first instead of paying for a full round. (default: False)

        Do not confuse either tag argument with the ``tags`` argument of
        :meth:`RapidataLeaderboard.get_standings`: that filters the standings you read
        back out, whereas these decide which prompts get matchups collected in the first
        place.

        Both match on the tag **value**; a tag's category is irrelevant. They are
        resolved when a run starts rather than snapshotted at creation, so re-tagging a
        prompt changes which future runs pick it up. They are read back via the
        read-only :attr:`RapidataLeaderboard.included_tags` /
        :attr:`RapidataLeaderboard.excluded_tags` and cannot be changed afterwards — to
        re-scope, create a new leaderboard.
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
                "Creating leaderboard %s with instruction %s, show_prompt %s, show_prompt_asset %s, inverse_ranking %s, level_of_detail %s, min_responses_per_matchup %s, audience_id %s, settings %s, included_tags %s, excluded_tags %s, vote_aggregation %s, skip_initial_run %s",
                name,
                instruction,
                show_prompt,
                show_prompt_asset,
                inverse_ranking,
                level_of_detail,
                min_responses_per_matchup,
                resolved_audience_id,
                settings,
                included_tags,
                excluded_tags,
                vote_aggregation.name,
                skip_initial_run,
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
                        includedTags=included_tags,
                        excludedTags=excluded_tags,
                        voteAggregation=vote_aggregation._to_backend_model(),
                        skipInitialRun=skip_initial_run,
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
                included_tags,
                excluded_tags,
                VoteAggregation._from_backend_model(
                    leaderboard_result.vote_aggregation
                ),
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

        If any sample fails to upload, a recovery sweep runs automatically: the
        intended samples are diffed against what the server actually holds and
        only the difference is re-uploaded. Anything still missing afterwards is
        logged with its reason; `participant.missing_counts(identifiers)` reports
        how many samples each identifier is still short.

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

                if failed_uploads:
                    # On a flaky link failures cluster in time, so the three
                    # immediate attempts all land in the same bad window. A
                    # sweep at the end of the batch is far enough removed to
                    # recover most of them, and diffing against the server first
                    # keeps it from duplicating a sample whose write outlived
                    # its timeout.
                    logger.warning(
                        "%s sample(s) failed; sweeping against server state before giving up",
                        len(failed_uploads),
                    )
                    recovered, failed_uploads = participant.retry_missing(
                        media,
                        identifiers,
                        data_type=data_type,
                    )
                    successful_uploads.extend(recovered)

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
                    for failure in failed_uploads[:_MAX_REPORTED_FAILURES]:
                        logger.error(failure.format_error_details())
                    if len(failed_uploads) > _MAX_REPORTED_FAILURES:
                        logger.error(
                            "... and %s more failed upload(s). Enable INFO logging to see each one.",
                            len(failed_uploads) - _MAX_REPORTED_FAILURES,
                        )
                    logger.warning(
                        "Some uploads failed. The model evaluation may be incomplete. "
                        "Call `participant.retry_missing(media, identifiers)` to try "
                        "again, or `participant.missing_counts(identifiers)` to see "
                        "which identifiers are still short."
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

        Unlike submitting each participant individually, a batch is evaluated
        symmetrically as one run: every participant is compared against every
        other and against the benchmark's already-submitted field.
        """
        from rapidata.api_client.models.participant_status import ParticipantStatus
        from rapidata.api_client.models.submit_participants_endpoint_input import (
            SubmitParticipantsEndpointInput,
        )

        with tracer.start_as_current_span("RapidataBenchmark.run"):
            created = [
                p for p in self.participants if p.status == ParticipantStatus.CREATED
            ]
            logger.info(f"Submitting {len(created)} participants in CREATED state")

            for start in range(0, len(created), _SUBMIT_BATCH_SIZE):
                batch = created[start : start + _SUBMIT_BATCH_SIZE]
                self._openapi_service.leaderboard.participant_api.participants_submit_post(
                    submit_participants_endpoint_input=SubmitParticipantsEndpointInput(
                        participantIds=[p.id for p in batch]
                    )
                )
                for participant in batch:
                    participant._status = ParticipantStatus.SUBMITTED

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
        country: Optional[list[str]] = None,
        language: Optional[list[str]] = None,
        gender: Optional[list[Gender]] = None,
        age_bucket: Optional[list[AgeGroup]] = None,
        occupation: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Returns an aggregated elo table of all leaderboards in the benchmark.

        The demographic filters compute the standings from only the votes cast by
        matching voters — e.g. the standings among women, or among US voters.
        ``gender`` and ``age_bucket`` are estimated (inferred); ``country`` and
        ``language`` are observed.

        Args:
            tags: Filter standings by these tags. If None, all tags are considered.
            leaderboard_ids: Filter to only include matchups from these leaderboards. If None, all leaderboards are considered.
            country: Only count votes from these countries (ISO-2 codes).
            language: Only count votes from these languages.
            gender: Only count votes from voters of these (estimated) genders.
            age_bucket: Only count votes from voters in these (estimated) age buckets.
            occupation: Only count votes from voters of these (estimated) occupations.
            run_id: Only count votes from this evaluation run.
        """
        import pandas as pd

        with tracer.start_as_current_span("get_overall_standings"):
            votes = demographic_filters(
                country, language, gender, age_bucket, occupation, run_id
            )
            participants = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_standings_query_get(
                benchmark_id=self.id,
                tags=in_filter(tags),
                leaderboard_id=in_filter(leaderboard_ids),
                country=votes.country,
                language=votes.language,
                gender=votes.gender,
                age_bucket=votes.age_bucket,
                occupation=votes.occupation,
                run_id=votes.run_id,
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
        country: Optional[list[str]] = None,
        language: Optional[list[str]] = None,
        gender: Optional[list[Gender]] = None,
        age_bucket: Optional[list[AgeGroup]] = None,
        occupation: Optional[list[str]] = None,
        run_id: Optional[str] = None,
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

        The demographic filters restrict the matrix to matchups decided by matching
        voters. ``gender`` and ``age_bucket`` are estimated (inferred); ``country``
        and ``language`` are observed.

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
            country: Only count votes from these countries (ISO-2 codes).
            language: Only count votes from these languages.
            gender: Only count votes from voters of these (estimated) genders.
            age_bucket: Only count votes from voters in these (estimated) age buckets.
            occupation: Only count votes from voters of these (estimated) occupations.
            run_id: Only count votes from this evaluation run.

        Returns:
            A pandas DataFrame indexed by participant name on both axes, where cell
            ``[i, j]`` holds the (optionally weighted) number of wins of the row
            participant over the column participant.
        """
        import pandas as pd

        with tracer.start_as_current_span("get_win_loss_matrix"):
            votes = demographic_filters(
                country, language, gender, age_bucket, occupation, run_id
            )
            result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_matrix_query_get(
                benchmark_id=self.id,
                tags=in_filter(tags),
                participant_id=in_filter(participant_ids),
                leaderboard_id=in_filter(leaderboard_ids),
                use_weighted_scoring=use_weighted_scoring,
                country=votes.country,
                language=votes.language,
                gender=votes.gender,
                age_bucket=votes.age_bucket,
                occupation=votes.occupation,
                run_id=votes.run_id,
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
        country: Optional[list[str]] = None,
        language: Optional[list[str]] = None,
        gender: Optional[list[Gender]] = None,
        age_bucket: Optional[list[AgeGroup]] = None,
        occupation: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Returns the demographic composition of the voters for this benchmark.

        One row per (dimension, bucket): the ``votes`` cast by that bucket and
        its ``share`` of the dimension's votes (a dimension's shares sum to 1).
        Every dimension (``AgeBucket``, ``Gender``, ``Occupation``, ``Country``,
        ``Language``) includes an ``"unknown"`` bucket for votes whose attribute
        could not be determined.

        ``AgeBucket``, ``Gender`` and ``Occupation`` are estimated (inferred from
        behaviour), not self-declared; ``Country`` and ``Language`` are observed.
        The demographic filters restrict the composition to matching voters.

        Args:
            tags: Only count votes on matchups with these tags. If None, all matchups are considered.
            leaderboard_ids: Only count votes from these leaderboards. If None, all leaderboards are considered.
            country: Only count votes from these countries (ISO-2 codes).
            language: Only count votes from these languages.
            gender: Only count votes from voters of these (estimated) genders.
            age_bucket: Only count votes from voters in these (estimated) age buckets.
            occupation: Only count votes from voters of these (estimated) occupations.
            run_id: Only count votes from this evaluation run. If None, all runs are considered.

        Returns:
            A pandas DataFrame with columns ``dimension``, ``value``, ``votes``, ``share``.
        """
        import pandas as pd

        with tracer.start_as_current_span("RapidataBenchmark.get_demographics"):
            votes = demographic_filters(
                country, language, gender, age_bucket, occupation, run_id
            )
            result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_demographics_get(
                benchmark_id=self.id,
                tags=in_filter(tags),
                leaderboard_id=in_filter(leaderboard_ids),
                country=votes.country,
                language=votes.language,
                gender=votes.gender,
                age_bucket=votes.age_bucket,
                occupation=votes.occupation,
                run_id=votes.run_id,
            )

            dimensions = result.dimensions
            dimension_buckets = {
                BenchmarkDemographicDimension.AGEBUCKET: dimensions.age_bucket,
                BenchmarkDemographicDimension.GENDER: dimensions.gender,
                BenchmarkDemographicDimension.OCCUPATION: dimensions.occupation,
                BenchmarkDemographicDimension.COUNTRY: dimensions.country,
                BenchmarkDemographicDimension.LANGUAGE: dimensions.language,
            }
            rows = [
                {
                    "dimension": dimension.value,
                    "value": bucket.value,
                    "votes": bucket.votes,
                    "share": bucket.share,
                }
                for dimension, buckets in dimension_buckets.items()
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
        country: Optional[list[str]] = None,
        language: Optional[list[str]] = None,
        gender: Optional[list[Gender]] = None,
        age_bucket: Optional[list[AgeGroup]] = None,
        occupation: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Returns the standings split by a demographic dimension of the voters.

        One row per (segment, model): how each demographic segment of voters
        ranks the models, alongside that segment's vote count. The segments
        include an ``"unknown"`` bucket. Scores are raw vote counts. For the
        overall standings across all voters, use :py:meth:`get_overall_standings`.

        ``AgeBucket``, ``Gender`` and ``Occupation`` are estimated (inferred), not
        self-declared; ``Country`` and ``Language`` are observed. The demographic
        filters narrow the voters before the split (e.g. break down by age within
        US voters only).

        Args:
            dimension: The :class:`BenchmarkDemographicDimension` to split by (``AgeBucket``, ``Gender``, ``Occupation``, ``Country`` or ``Language``).
            tags: Only count votes on matchups with these tags. If None, all matchups are considered.
            leaderboard_ids: Only count votes from these leaderboards. If None, all leaderboards are considered.
            country: Only count votes from these countries (ISO-2 codes).
            language: Only count votes from these languages.
            gender: Only count votes from voters of these (estimated) genders.
            age_bucket: Only count votes from voters in these (estimated) age buckets.
            occupation: Only count votes from voters of these (estimated) occupations.
            run_id: Only count votes from this evaluation run. If None, all runs are considered.

        Returns:
            A pandas DataFrame with columns ``segment``, ``segment_votes``, ``name``, ``wins``, ``total_matches``, ``score``.
        """
        import pandas as pd

        with tracer.start_as_current_span("RapidataBenchmark.get_standings_breakdown"):
            votes = demographic_filters(
                country, language, gender, age_bucket, occupation, run_id
            )
            result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_standings_breakdown_get(
                benchmark_id=self.id,
                dimension=BenchmarkDemographicDimension(dimension),
                tags=in_filter(tags),
                leaderboard_id=in_filter(leaderboard_ids),
                country=votes.country,
                language=votes.language,
                gender=votes.gender,
                age_bucket=votes.age_bucket,
                occupation=votes.occupation,
                run_id=votes.run_id,
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

    def __str__(self) -> str:
        return f"RapidataBenchmark(name={self.name}, id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
