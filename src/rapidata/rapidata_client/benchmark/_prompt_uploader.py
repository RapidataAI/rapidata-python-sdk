from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from opentelemetry import context as otel_context
from tqdm.auto import tqdm

from rapidata.rapidata_client.config import logger, rapidata_config, tracer
from rapidata.rapidata_client.benchmark.prompt_metadata import Origin, Tag
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService


@dataclass
class BenchmarkPrompt:
    """A single prompt to register on a benchmark."""

    identifier: str
    prompt: str | None = None
    prompt_asset: str | None = None
    taggings: list[Tag] = field(default_factory=list)
    origin: Origin | None = None


class BenchmarkPromptUploader:
    """Registers prompts on a benchmark — one at a time or many concurrently.

    Keeps the upload mechanics (asset upload, the prompt POST, concurrency,
    progress, failure handling) out of the ``RapidataBenchmark`` entity.
    """

    def __init__(self, benchmark_id: str, openapi_service: OpenAPIService) -> None:
        self._benchmark_id = benchmark_id
        self._openapi_service = openapi_service
        self._asset_uploader = AssetUploader(openapi_service)

    def upload(self, prompt: BenchmarkPrompt) -> None:
        """Register a single prompt. Performs the network calls only."""
        from rapidata.api_client.models.create_prompt_for_benchmark_endpoint_input import (
            CreatePromptForBenchmarkEndpointInput,
        )
        from rapidata.api_client.models.i_asset_input_existing_asset_input import (
            IAssetInputExistingAssetInput,
        )
        from rapidata.api_client.models.i_asset_input import IAssetInput
        from rapidata.api_client.models.prompt_origin import PromptOrigin
        from rapidata.api_client.models.prompt_tagging import PromptTagging

        self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_prompt_post(
            benchmark_id=self._benchmark_id,
            create_prompt_for_benchmark_endpoint_input=CreatePromptForBenchmarkEndpointInput(
                identifier=prompt.identifier,
                prompt=prompt.prompt,
                promptAsset=(
                    IAssetInput(
                        actual_instance=IAssetInputExistingAssetInput(
                            _t="ExistingAssetInput",
                            name=self._asset_uploader.upload_asset(prompt.prompt_asset),
                        )
                    )
                    if prompt.prompt_asset is not None
                    else None
                ),
                # `tags` is deprecated (values only) but still populated so an
                # older backend that doesn't yet read `taggings` keeps working.
                tags=[tag.value for tag in prompt.taggings],
                taggings=[
                    PromptTagging(value=tag.value, category=tag.category)
                    for tag in prompt.taggings
                ],
                origin=(
                    PromptOrigin(value=prompt.origin.value)
                    if prompt.origin is not None
                    else None
                ),
            ),
        )

    def upload_many(self, prompts: list[BenchmarkPrompt]) -> list[BenchmarkPrompt]:
        """Register many prompts concurrently.

        Every prompt is attempted even if some fail; failures are logged and the
        prompts that succeeded are returned in input order. Raises a
        ``RuntimeError`` only if every prompt failed.
        """
        current_context = otel_context.get_current()
        failures: dict[str, Exception] = {}

        def upload_one(prompt: BenchmarkPrompt) -> None:
            token = otel_context.attach(current_context)
            try:
                self.upload(prompt)
            except Exception as e:
                failures[prompt.identifier] = e
                logger.error(
                    "Failed to upload prompt %s: %s", prompt.identifier, str(e)
                )
            finally:
                otel_context.detach(token)

        with tracer.start_as_current_span("BenchmarkPromptUploader.upload_many"):
            with ThreadPoolExecutor(
                max_workers=rapidata_config.upload.maxWorkers
            ) as executor:
                futures = [executor.submit(upload_one, prompt) for prompt in prompts]
                with tqdm(
                    total=len(prompts),
                    desc="Uploading prompts",
                    disable=rapidata_config.logging.silent_mode,
                ) as pbar:
                    for future in as_completed(futures):
                        future.result()
                        pbar.update(1)

        if failures:
            logger.warning(
                "%d of %d prompts failed to upload and were skipped: %s",
                len(failures),
                len(prompts),
                list(failures.keys()),
            )
            if len(failures) == len(prompts):
                raise RuntimeError(
                    "Failed to upload any prompts to the benchmark. See logs for details."
                )

        return [p for p in prompts if p.identifier not in failures]
