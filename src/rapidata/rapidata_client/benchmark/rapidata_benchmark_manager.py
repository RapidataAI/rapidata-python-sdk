from __future__ import annotations

from typing import Literal, Optional, Union
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark
from rapidata.rapidata_client.benchmark.demographics._demographics_api import (
    BENCHMARK_FILTER_FIELDS,
)
from rapidata.rapidata_client.benchmark.demographics.models import (
    BenchmarkDemographics,
    BenchmarkStandingsBreakdown,
)
from rapidata.api_client.models.create_benchmark_endpoint_input import (
    CreateBenchmarkEndpointInput,
)
from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
    AudienceAudienceIdJobsGetJobIdParameter,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, tracer

# The demographic dimension to break standings down by, as accepted by the
# breakdown endpoint's `dimension` query parameter.
BreakdownDimension = Literal["AgeBucket", "Gender", "Occupation", "Country", "Language"]


class RapidataBenchmarkManager:
    """
    A manager for benchmarks.

    Used to create and retrieve benchmarks.

    A benchmark is a collection of leaderboards.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self.__openapi_service = openapi_service

    def create_new_benchmark(
        self,
        name: str,
        identifiers: Optional[list[str]] = None,
        prompts: Optional[list[str | None] | list[str]] = None,
        prompt_assets: Optional[list[str | None] | list[str]] = None,
        tags: Optional[list[list[str] | None] | list[list[str]]] = None,
    ) -> RapidataBenchmark:
        """
        Creates a new benchmark with the given name, identifiers, prompts, and media assets.
        Everything is matched up by the indexes of the lists.

        prompts or identifiers must be provided, as well as prompts or prompt_assets.

        Args:
            name: The name of the benchmark.
            identifiers: The identifiers of the prompts/assets/tags that will be used to match up the media. If not provided, it will use the prompts as the identifiers.
            prompts: The prompts that will be registered for the benchmark.
            prompt_assets: The prompt assets that will be registered for the benchmark.
            tags: The tags that will be associated with the prompts to use for filtering the leaderboard results. They will NOT be shown to the users.

        Example:
            ```python
            name = "Example Benchmark"
            identifiers = ["id1", "id2", "id3"]
            prompts = ["prompt 1", "prompt 2", "prompt 3"]
            prompt_assets = ["https://assets.rapidata.ai/prompt_1.jpg", "https://assets.rapidata.ai/prompt_2.jpg", "https://assets.rapidata.ai/prompt_3.jpg"]
            tags = [["tag1", "tag2"], ["tag2"], ["tag2", "tag3"]]

            benchmark = create_new_benchmark(name=name, identifiers=identifiers, prompts=prompts, prompt_assets=prompt_assets, tags=tags)
            ```
        """
        with tracer.start_as_current_span(
            "RapidataBenchmarkManager.create_new_benchmark"
        ):
            if not isinstance(name, str):
                raise ValueError("Name must be a string.")

            logger.info("Creating new benchmark %s", name)

            benchmark_result = (
                self.__openapi_service.leaderboard.benchmark_api.benchmark_post(
                    create_benchmark_endpoint_input=CreateBenchmarkEndpointInput(
                        name=name,
                    )
                )
            )

            logger.info("Benchmark created with id %s", benchmark_result.id)

            benchmark = RapidataBenchmark(
                name, benchmark_result.id, self.__openapi_service
            )

            benchmark.add_prompts(identifiers, prompts, prompt_assets, tags)

            return benchmark

    def get_benchmark_by_id(self, id: str) -> RapidataBenchmark:
        """
        Returns a benchmark by its ID.
        """
        with tracer.start_as_current_span(
            "RapidataBenchmarkManager.get_benchmark_by_id"
        ):
            benchmark_result = self.__openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_get(
                benchmark_id=id
            )
            return RapidataBenchmark(
                benchmark_result.name, benchmark_result.id, self.__openapi_service
            )

    def find_benchmarks(
        self, name: str = "", amount: int = 10, page: int = 1
    ) -> list[RapidataBenchmark]:
        """
        Returns a list of benchmarks by their name.

        Args:
            name (str, optional): The name of the benchmark - matching benchmark will contain the name. Defaults to "" for any benchmark.
            amount (int, optional): The amount of benchmarks to return. Defaults to 10.
            page (int, optional): The page of benchmarks to return. Defaults to 1.

        Returns:
            list[RapidataBenchmark]: A list of RapidataBenchmark instances.
        """
        with tracer.start_as_current_span("RapidataBenchmarkManager.find_benchmarks"):
            benchmark_result = (
                self.__openapi_service.leaderboard.benchmark_api.benchmarks_get(
                    page=page,
                    page_size=amount,
                    name=AudienceAudienceIdJobsGetJobIdParameter(contains=name),
                    sort=["-created_at"],
                )
            )
            return [
                RapidataBenchmark(benchmark.name, benchmark.id, self.__openapi_service)
                for benchmark in benchmark_result.items
            ]

    def get_demographics(
        self,
        benchmark_id: str,
        run_id: Optional[str] = None,
        filters: Optional[dict[str, Union[str, list[str]]]] = None,
    ) -> BenchmarkDemographics:
        """
        Returns the demographic composition of the voters for a benchmark.

        The result reports, per dimension (``ageBucket``, ``gender``,
        ``occupation``, ``country``, ``language``), how the votes split across
        that dimension's buckets — both the raw vote count and the share of the
        total. Each dimension includes an ``"unknown"`` bucket for votes whose
        attribute could not be determined, and the shares of a dimension sum to 1.

        Note that ``ageBucket``, ``gender`` and ``occupation`` are **estimated**
        (inferred from behaviour), not self-declared by the annotators;
        ``country`` and ``language`` are observed.

        Args:
            benchmark_id: The id of the benchmark.
            run_id: Restrict the composition to a single evaluation run. If None, all runs are considered.
            filters: Additional filters on the underlying votes, keyed by field name. Accepts the same fields as the standings query (e.g. ``country``, ``language``, ``gender``, ``age_bucket``, ``occupation``, ``tags``, ``leaderboard_id``, ``participant_id``, ``prompt_identifier``). Each value is a string or list of strings matched with ``in`` semantics.

        Returns:
            A BenchmarkDemographics describing the voter composition.
        """
        with tracer.start_as_current_span("RapidataBenchmarkManager.get_demographics"):
            return self.__openapi_service.leaderboard.benchmark_demographics_api.get_demographics(
                benchmark_id=benchmark_id,
                filters=self.__build_filters(filters, run_id),
            )

    def get_standings_breakdown(
        self,
        benchmark_id: str,
        dimension: BreakdownDimension,
        run_id: Optional[str] = None,
        filters: Optional[dict[str, Union[str, list[str]]]] = None,
    ) -> BenchmarkStandingsBreakdown:
        """
        Returns the benchmark standings broken down by a demographic dimension.

        Alongside the global standings, this returns one segment per bucket of
        ``dimension`` (including an ``"unknown"`` bucket), each with that
        segment's raw vote count and its own standings. This shows how different
        voter groups rank the models relative to each other.

        Segments are **raw vote counts**. Note that the ``AgeBucket``, ``Gender``
        and ``Occupation`` dimensions are **estimated** (inferred), not
        self-declared.

        Args:
            benchmark_id: The id of the benchmark.
            dimension: The demographic dimension to break the standings down by. One of "AgeBucket", "Gender", "Occupation", "Country", "Language".
            run_id: Restrict the breakdown to a single evaluation run. If None, all runs are considered.
            filters: Additional filters on the underlying votes, keyed by field name (same fields as :py:meth:`get_demographics`). Each value is a string or list of strings matched with ``in`` semantics.

        Returns:
            A BenchmarkStandingsBreakdown with the global standings and per-segment standings.
        """
        with tracer.start_as_current_span(
            "RapidataBenchmarkManager.get_standings_breakdown"
        ):
            if dimension not in BreakdownDimension.__args__:
                raise ValueError(
                    "Dimension must be one of: "
                    + ", ".join(BreakdownDimension.__args__)
                )

            return self.__openapi_service.leaderboard.benchmark_demographics_api.get_standings_breakdown(
                benchmark_id=benchmark_id,
                dimension=dimension,
                filters=self.__build_filters(filters, run_id),
            )

    @staticmethod
    def __build_filters(
        filters: Optional[dict[str, Union[str, list[str]]]],
        run_id: Optional[str],
    ) -> dict[str, AudienceAudienceIdJobsGetJobIdParameter]:
        raw: dict[str, Union[str, list[str]]] = dict(filters or {})
        if run_id is not None:
            raw["run_id"] = run_id

        built: dict[str, AudienceAudienceIdJobsGetJobIdParameter] = {}
        for field, value in raw.items():
            if field not in BENCHMARK_FILTER_FIELDS:
                raise ValueError(
                    f"Unknown filter field '{field}'. Allowed fields: "
                    + ", ".join(BENCHMARK_FILTER_FIELDS)
                )
            values = [value] if isinstance(value, str) else list(value)
            param = AudienceAudienceIdJobsGetJobIdParameter()
            param.var_in = values
            built[field] = param
        return built
