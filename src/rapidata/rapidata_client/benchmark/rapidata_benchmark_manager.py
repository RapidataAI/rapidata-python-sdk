from typing import Optional, cast
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark
from rapidata.api_client.models.create_benchmark_model import CreateBenchmarkModel
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion
from rapidata.api_client.models.sort_direction import SortDirection
from rapidata.api_client.models.filter_operator import FilterOperator
from rapidata.rapidata_client.config import logger, tracer


class RapidataBenchmarkManager:
    """
    A manager for benchmarks.

    Used to create and retrieve benchmarks.

    A benchmark is a collection of leaderboards.

    Args:
        openapi_service: The OpenAPIService instance for API interaction.
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

            if identifiers:
                if not len(set(identifiers)) == len(identifiers):
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
                if not len(set(prompts)) == len(prompts):
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

            # At this point, all variables are guaranteed to be lists, not None
            assert prompts is not None
            assert prompt_assets is not None
            assert tags is not None

            if not (expected_length == len(prompts) == len(prompt_assets) == len(tags)):
                raise ValueError(
                    "Identifiers, prompts, media assets, and tags must have the same length or set to None."
                )

            logger.info("Creating new benchmark %s", name)

            benchmark_result = self.__openapi_service.benchmark_api.benchmark_post(
                create_benchmark_model=CreateBenchmarkModel(
                    name=name,
                )
            )

            logger.info("Benchmark created with id %s", benchmark_result.id)

            benchmark = RapidataBenchmark(
                name, benchmark_result.id, self.__openapi_service
            )

            for identifier, prompt, asset, tag in zip(
                identifiers, prompts, prompt_assets, tags
            ):
                benchmark.add_prompt(identifier, prompt, asset, tag)

            return benchmark

    def get_benchmark_by_id(self, id: str) -> RapidataBenchmark:
        """
        Returns a benchmark by its ID.
        """
        with tracer.start_as_current_span(
            "RapidataBenchmarkManager.get_benchmark_by_id"
        ):
            benchmark_result = (
                self.__openapi_service.benchmark_api.benchmark_benchmark_id_get(
                    benchmark_id=id
                )
            )
            return RapidataBenchmark(
                benchmark_result.name, benchmark_result.id, self.__openapi_service
            )

    def find_benchmarks(
        self, name: str = "", amount: int = 10
    ) -> list[RapidataBenchmark]:
        """
        Returns a list of benchmarks by their name.
        """
        with tracer.start_as_current_span("RapidataBenchmarkManager.find_benchmarks"):
            benchmark_result = self.__openapi_service.benchmark_api.benchmarks_get(
                QueryModel(
                    page=PageInfo(index=1, size=amount),
                    filter=RootFilter(
                        filters=[
                            Filter(
                                field="Name",
                                operator=FilterOperator.CONTAINS,
                                value=name,
                            )
                        ]
                    ),
                    sortCriteria=[
                        SortCriterion(
                            direction=SortDirection.DESC, propertyName="CreatedAt"
                        )
                    ],
                )
            )
            return [
                RapidataBenchmark(benchmark.name, benchmark.id, self.__openapi_service)
                for benchmark in benchmark_result.items
            ]
