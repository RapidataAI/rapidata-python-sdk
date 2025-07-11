from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark
from rapidata.api_client.models.create_benchmark_model import CreateBenchmarkModel
from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.query_model import QueryModel
from rapidata.api_client.models.page_info import PageInfo
from rapidata.api_client.models.root_filter import RootFilter
from rapidata.api_client.models.filter import Filter
from rapidata.api_client.models.sort_criterion import SortCriterion

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

    def create_new_benchmark(self, 
                             name: str,
                             identifiers: list[str],
                             prompts: list[str],
                             ) -> RapidataBenchmark:
        """
        Creates a new benchmark with the given name, prompts, and leaderboards.

        Args:
            name: The name of the benchmark.
            prompts: The prompts that will be registered for the benchmark.
        """
        if not isinstance(name, str):
            raise ValueError("Name must be a string.")
        
        if not isinstance(prompts, list) or not all(isinstance(prompt, str) for prompt in prompts):
            raise ValueError("Prompts must be a list of strings.")
        
        if not isinstance(identifiers, list) or not all(isinstance(identifier, str) for identifier in identifiers):
            raise ValueError("Identifiers must be a list of strings.")
        
        if len(identifiers) != len(prompts):
            raise ValueError("Identifiers and prompts must have the same length.")
        
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Identifiers must be unique.")

        benchmark_result = self.__openapi_service.benchmark_api.benchmark_post(
            create_benchmark_model=CreateBenchmarkModel(
                name=name,
            )
        )

        benchmark = RapidataBenchmark(name, benchmark_result.id, self.__openapi_service)
        for identifier, prompt in zip(identifiers, prompts):
            benchmark.add_prompt(identifier, prompt)

        return benchmark
    
    def get_benchmark_by_id(self, id: str) -> RapidataBenchmark:
        """
        Returns a benchmark by its ID.
        """
        benchmark_result = self.__openapi_service.benchmark_api.benchmark_benchmark_id_get(
            benchmark_id=id
        )
        return RapidataBenchmark(benchmark_result.name, benchmark_result.id, self.__openapi_service)
    
    def find_benchmarks(self, name: str = "", amount: int = 10) -> list[RapidataBenchmark]:
        """
        Returns a list of benchmarks by their name.
        """
        benchmark_result = self.__openapi_service.benchmark_api.benchmarks_get(
            QueryModel(
                page=PageInfo(index=1, size=amount),
                filter=RootFilter(filters=[Filter(field="Name", operator="Contains", value=name)]),
                sortCriteria=[SortCriterion(direction="Desc", propertyName="CreatedAt")]
            )
        )
        return [RapidataBenchmark(benchmark.name, benchmark.id, self.__openapi_service) for benchmark in benchmark_result.items]
