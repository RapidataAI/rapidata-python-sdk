from rapidata.rapidata_client.benchmark.rapidat_benchmark import RapidataBenchmark
from rapidata.api_client.models.create_benchmark_model import CreateBenchmarkModel
from rapidata.service.openapi_service import OpenAPIService

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

        benchmark_result = self.__openapi_service.benchmark_api.benchmark_post(
            create_benchmark_model=CreateBenchmarkModel(
                name=name,
            )
        )

        benchmark = RapidataBenchmark(name, benchmark_result.id, self.__openapi_service)
        for prompt in prompts:
            benchmark.add_prompt(prompt)

        return benchmark
