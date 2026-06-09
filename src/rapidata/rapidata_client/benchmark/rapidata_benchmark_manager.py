from typing import Optional
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark
from rapidata.api_client.models.create_benchmark_endpoint_input import (
    CreateBenchmarkEndpointInput,
)
from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
    AudienceAudienceIdJobsGetJobIdParameter,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger, tracer


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
