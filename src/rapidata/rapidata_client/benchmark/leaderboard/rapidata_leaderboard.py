from __future__ import annotations
import urllib.parse
import webbrowser
from colorama import Fore
from typing import Optional, TYPE_CHECKING

from rapidata.rapidata_client.config import logger, managed_print, tracer
from rapidata.rapidata_client.benchmark._detail_mapper import (
    DetailMapper,
    LevelOfDetail,
    ResolvedLevelOfDetail,
)
from rapidata.rapidata_client.benchmark._vote_filters import (
    demographic_filters,
    in_filter,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.update_leaderboard_endpoint_input import (
    UpdateLeaderboardEndpointInput,
)

if TYPE_CHECKING:
    import pandas as pd
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob
    from rapidata.rapidata_client.filter.models.gender import Gender
    from rapidata.rapidata_client.filter.models.age_group import AgeGroup


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

    def __init__(
        self,
        name: str,
        instruction: str,
        show_prompt: bool,
        show_prompt_asset: bool,
        inverse_ranking: bool,
        response_budget: int,
        min_responses_per_matchup: int,
        benchmark_id: str,
        id: str,
        openapi_service: OpenAPIService,
    ):
        self.__openapi_service = openapi_service
        self.__name = name
        self.__instruction = instruction
        self.__show_prompt = show_prompt
        self.__show_prompt_asset = show_prompt_asset
        self.__inverse_ranking = inverse_ranking
        self.__response_budget = response_budget
        self.__min_responses_per_matchup = min_responses_per_matchup
        self.__benchmark_id = benchmark_id
        self.id = id
        self.__leaderboard_page = f"https://app.{self.__openapi_service.environment}/mri/benchmarks/{self.__benchmark_id}/leaderboard/{self.id}"

    @property
    def response_budget(self) -> int:
        """
        The leaderboard's response budget — the total number of comparison responses
        collected per model evaluation.

        This is the raw number behind :attr:`level_of_detail`; read it when you need
        the exact budget rather than the named level (which is ``"custom"`` for
        budgets that don't match a named level).
        """
        return self.__response_budget

    @property
    def level_of_detail(self) -> ResolvedLevelOfDetail:
        """
        The level of detail of the leaderboard.

        This is a friendly name for the leaderboard's :attr:`response_budget` — the
        total number of comparison responses collected per model evaluation. A larger
        budget buys more matchups and therefore more precise standings, at the cost
        of a slower and more expensive evaluation. The named levels map to these
        budgets: ``'debug'`` (20), ``'low'`` (2,000), ``'medium'`` (4,000),
        ``'high'`` (8,000), ``'very high'`` (16,000). Any other budget reads back as
        ``'custom'`` — use :attr:`response_budget` to get the exact number.
        """
        return DetailMapper.get_level_of_detail(self.__response_budget)

    @level_of_detail.setter
    def level_of_detail(self, level_of_detail: LevelOfDetail | int):
        """
        Sets the level of detail (response budget) of the leaderboard.

        Accepts one of the named levels or a positive integer for a custom response
        budget. Takes effect for future evaluations; already-computed standings are
        not recomputed.
        """
        with tracer.start_as_current_span("RapidataLeaderboard.level_of_detail.setter"):
            logger.debug(f"Setting level of detail to {level_of_detail}")
            self.__response_budget = DetailMapper.resolve_budget(level_of_detail)
            self._update_config()

    @property
    def min_responses_per_matchup(self) -> int:
        """
        Returns the minimum number of responses required to be considered for the leaderboard.
        """
        return self.__min_responses_per_matchup

    @min_responses_per_matchup.setter
    def min_responses_per_matchup(self, min_responses: int):
        """
        Sets the minimum number of responses required to be considered for the leaderboard.
        """
        with tracer.start_as_current_span(
            "RapidataLeaderboard.min_responses_per_matchup.setter"
        ):
            if not isinstance(min_responses, int):
                raise ValueError("Min responses per matchup must be an integer")

            if min_responses < 3:
                raise ValueError("Min responses per matchup must be at least 3")

            logger.debug(
                f"Setting min responses per matchup to {min_responses} for leaderboard {self.name}"
            )
            self.__min_responses_per_matchup = min_responses
            self._update_config()

    @property
    def show_prompt_asset(self) -> bool:
        """
        Returns whether the prompt asset is shown to the users.
        """
        return self.__show_prompt_asset

    @property
    def inverse_ranking(self) -> bool:
        """
        Returns whether the ranking is inverse.
        """
        return self.__inverse_ranking

    @property
    def show_prompt(self) -> bool:
        """
        Returns whether the prompt is shown to the users.
        """
        return self.__show_prompt

    @property
    def instruction(self) -> str:
        """
        Returns the instruction of the leaderboard.
        """
        return self.__instruction

    @property
    def name(self) -> str:
        """
        Returns the name of the leaderboard.
        """
        return self.__name

    @name.setter
    def name(self, name: str):
        """
        Sets the name of the leaderboard.
        """
        with tracer.start_as_current_span("RapidataLeaderboard.name.setter"):
            if not isinstance(name, str):
                raise ValueError("Name must be a string")
            if len(name) < 1:
                raise ValueError("Name must be at least 1 character long")

            self.__name = name
            self._update_config()

    @property
    def jobs(self) -> list[RapidataJob]:
        """
        Returns all Rapidata jobs that have run for this leaderboard.

        Every model evaluation on the leaderboard is carried out by a job. This
        collects the jobs across all runs of the leaderboard, most recent first.

        Returns:
            A list of RapidataJob instances, one per run that has an associated job.
        """
        with tracer.start_as_current_span("RapidataLeaderboard.jobs"):
            from rapidata.rapidata_client.job.rapidata_job_manager import (
                RapidataJobManager,
            )

            job_manager = RapidataJobManager(self.__openapi_service)

            current_page = 1
            job_ids: list[str] = []

            while True:
                runs_result = self.__openapi_service.leaderboard.leaderboard_api.leaderboard_leaderboard_id_runs_get(
                    leaderboard_id=self.id,
                    page=current_page,
                    page_size=100,
                    sort=["-created_at"],
                )

                if runs_result.total_pages is None:
                    raise ValueError(
                        "An error occurred while fetching runs: total_pages is None"
                    )

                job_ids.extend(
                    run.job_id for run in runs_result.items if run.job_id is not None
                )

                if current_page >= runs_result.total_pages:
                    break

                current_page += 1

            return [job_manager.get_job_by_id(job_id) for job_id in job_ids]

    def get_standings(
        self,
        tags: Optional[list[str]] = None,
        country: Optional[list[str]] = None,
        language: Optional[list[str]] = None,
        gender: Optional[list[Gender]] = None,
        age_bucket: Optional[list[AgeGroup]] = None,
        occupation: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> "pd.DataFrame":
        """
        Returns the standings of the leaderboard.

        The demographic filters compute the standings from only the votes cast by
        matching voters — e.g. the standings among women, or among US voters.
        ``gender`` and ``age_bucket`` are estimated (inferred); ``country`` and
        ``language`` are observed.

        Args:
            tags: The matchups with these tags should be used to create the standings.
                If tags are None, all matchups will be considered.
                If tags are empty, no matchups will be considered.
            country: Only count votes from these countries (ISO-2 codes).
            language: Only count votes from these languages.
            gender: Only count votes from voters of these (estimated) genders.
            age_bucket: Only count votes from voters in these (estimated) age buckets.
            occupation: Only count votes from voters of these (estimated) occupations.
            run_id: Only count votes from this evaluation run.

        Returns:
            A pandas DataFrame containing the standings of the leaderboard.
        """
        with tracer.start_as_current_span("RapidataLeaderboard.get_standings"):
            votes = demographic_filters(
                country, language, gender, age_bucket, occupation, run_id
            )
            participants = self.__openapi_service.leaderboard.leaderboard_api.leaderboard_leaderboard_id_standings_query_get(
                leaderboard_id=self.id,
                tags=in_filter(tags),
                country=votes.country,
                language=votes.language,
                gender=votes.gender,
                age_bucket=votes.age_bucket,
                occupation=votes.occupation,
                run_id=votes.run_id,
            )

            import pandas as pd

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
        use_weighted_scoring: Optional[bool] = None,
        country: Optional[list[str]] = None,
        language: Optional[list[str]] = None,
        gender: Optional[list[Gender]] = None,
        age_bucket: Optional[list[AgeGroup]] = None,
        occupation: Optional[list[str]] = None,
        run_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Returns the pairwise win/loss matrix for the participants in this leaderboard.

        The returned DataFrame is square, with participant names on both the index
        (rows) and columns. Cell ``[i, j]`` is how often participant ``i`` (row) beat
        participant ``j`` (column) in their direct matchups. Read a row to see how a
        model did against every opponent; the diagonal (a model against itself) is
        always 0. This is the head-to-head breakdown behind :meth:`get_standings`,
        which collapses the same matchups into a single Elo score per model.

        The demographic filters restrict the matrix to matchups decided by matching
        voters. ``gender`` and ``age_bucket`` are estimated (inferred); ``country``
        and ``language`` are observed.

        Args:
            tags: Only count matchups carrying one of these prompt tags. If None,
                every matchup on the leaderboard is included; if an empty list, none are.
            use_weighted_scoring: If True, each matchup is weighted by the responding
                annotators' reliability (``userScore``) instead of being counted as a
                plain win, so cells hold weighted sums (floats) rather than raw counts.
                If False, cells are raw win counts. When None (default), the server
                applies the leaderboard's configured default.
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
        with tracer.start_as_current_span("RapidataLeaderboard.get_win_loss_matrix"):
            votes = demographic_filters(
                country, language, gender, age_bucket, occupation, run_id
            )
            result = self.__openapi_service.leaderboard.leaderboard_api.leaderboard_leaderboard_id_matrix_query_get(
                leaderboard_id=self.id,
                tags=in_filter(tags),
                use_weighted_scoring=use_weighted_scoring,
                country=votes.country,
                language=votes.language,
                gender=votes.gender,
                age_bucket=votes.age_bucket,
                occupation=votes.occupation,
                run_id=votes.run_id,
            )

            import pandas as pd

            return pd.DataFrame(
                data=result.data,
                index=pd.Index(result.index),
                columns=pd.Index(result.columns),
            )

    def view(self) -> None:
        """
        Views the leaderboard.
        """
        logger.info("Opening leaderboard page in browser...")
        could_open_browser = webbrowser.open(self.__leaderboard_page)
        if not could_open_browser:
            encoded_url = urllib.parse.quote(
                self.__leaderboard_page, safe="%/:=&?~#+!$,;'@()*[]"
            )
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )

    def _custom_config(self, response_budget: int, min_responses_per_matchup: int):
        self.__response_budget = response_budget
        self.__min_responses_per_matchup = min_responses_per_matchup
        self._update_config()

    def _update_config(self):
        with tracer.start_as_current_span("RapidataLeaderboard._update_config"):
            self.__openapi_service.leaderboard.leaderboard_api.leaderboard_leaderboard_id_patch(
                leaderboard_id=self.id,
                update_leaderboard_endpoint_input=UpdateLeaderboardEndpointInput(
                    name=self.__name,
                    responseBudget=self.__response_budget,
                    minResponses=self.__min_responses_per_matchup,
                ),
            )

    def __str__(self) -> str:
        return f"RapidataLeaderboard(name={self.name}, instruction={self.instruction}, show_prompt={self.show_prompt}, leaderboard_id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
