from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Literal
from tqdm.auto import tqdm

from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.config._backoff import backoff_delay
from rapidata.rapidata_client.config.rapidata_config import rapidata_config
from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)

from opentelemetry import context as otel_context
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.benchmark.participant.sample_upload import SampleUpload
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload


from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.participant_status import ParticipantStatus


class BenchmarkParticipant:
    """A participant (model) in a benchmark evaluation.

    Represents a model that has been added to a benchmark for evaluation.
    Provides methods to upload media and submit the participant for evaluation.

    Args:
        name: The name of the participant/model.
        id: The unique identifier of the participant.
        openapi_service: The OpenAPI service for API communication.
        benchmark_id: The id of the benchmark the participant belongs to.
        status: The current status of the participant.
    """

    def __init__(
        self,
        name: str,
        id: str,
        openapi_service: OpenAPIService,
        benchmark_id: str,
        status: ParticipantStatus = ParticipantStatus.CREATED,
    ):
        self.name = name
        self.id = id
        self._openapi_service = openapi_service
        self._benchmark_id = benchmark_id
        self._asset_uploader = AssetUploader(openapi_service)
        self._status = status
        self._failed_samples: list[FailedUpload[SampleUpload]] = []

    @property
    def status(self) -> ParticipantStatus:
        """The current status of the participant."""
        return self._status

    @property
    def failed_samples(self) -> list[FailedUpload[SampleUpload]]:
        """The samples that failed in the most recent upload on this participant.

        Each entry carries the media/identifier pair plus the failure reason and
        backend trace id, so a failed batch can be re-submitted without
        reconstructing the pairs from the logs. Populated by
        :meth:`upload_media` and :meth:`retry_missing` — and therefore by
        ``benchmark.add_model``, which calls them.
        """
        return list(self._failed_samples)

    def get_elo(self) -> float | None:
        """Returns the participant's current Elo score in the benchmark.

        The score is aggregated across all of the benchmark's leaderboards and
        reflects the latest computed standings.

        Returns:
            The Elo score, or ``None`` if it has not been computed yet (for
            example when the participant has not been evaluated).
        """
        # The full standings must be requested: scores are recomputed relative
        # to the whole field on every call, so filtering to a single participant
        # would yield a meaningless score.
        with tracer.start_as_current_span("BenchmarkParticipant.get_elo"):
            result = self._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_standings_query_get(
                benchmark_id=self._benchmark_id,
            )

            for standing in result.items:
                if standing.id == self.id:
                    return (
                        round(standing.score, 2) if standing.score is not None else None
                    )

            return None

    def delete(self) -> None:
        """Deletes the participant from the benchmark.

        This removes the participant and its uploaded media. The operation
        cannot be undone.
        """
        with tracer.start_as_current_span("BenchmarkParticipant.delete"):
            self._openapi_service.leaderboard.participant_api.participant_participant_id_delete(
                participant_id=self.id
            )

    def run(self) -> None:
        """Submits the participant for evaluation.

        After uploading media, call this method to submit the participant
        so that it enters the evaluation pipeline.
        """
        self._openapi_service.leaderboard.participant_api.participants_participant_id_submit_post(
            participant_id=self.id
        )
        self._status = ParticipantStatus.SUBMITTED

    def disable(self) -> None:
        """Disables the participant in the benchmark.

        A disabled participant is excluded from evaluation and the computed
        standings. Use :meth:`enable` to reverse this.
        """
        with tracer.start_as_current_span("BenchmarkParticipant.disable"):
            self._openapi_service.leaderboard.participant_api.participant_participant_id_disable_post(
                participant_id=self.id
            )
            self._status = ParticipantStatus.DISABLED

    def enable(self) -> None:
        """Re-enables a previously disabled participant.

        The participant returns to the ``Submitted`` state and is included in
        evaluation and standings again.
        """
        with tracer.start_as_current_span("BenchmarkParticipant.enable"):
            self._openapi_service.leaderboard.participant_api.participant_participant_id_enable_post(
                participant_id=self.id
            )
            self._status = ParticipantStatus.SUBMITTED

    def rename(self, name: str) -> None:
        """Renames the participant.

        Args:
            name: The new name of the participant.
        """
        from rapidata.api_client.models.update_participant_name_endpoint_input import (
            UpdateParticipantNameEndpointInput,
        )

        with tracer.start_as_current_span("BenchmarkParticipant.rename"):
            self._openapi_service.leaderboard.participant_api.participant_participant_id_name_put(
                participant_id=self.id,
                update_participant_name_endpoint_input=UpdateParticipantNameEndpointInput(
                    name=name
                ),
            )
            self.name = name

    def __str__(self) -> str:
        return f"BenchmarkParticipant(name={self.name}, id={self.id}, status={self._status})"

    def __repr__(self) -> str:
        return self.__str__()

    def _process_single_sample_upload(
        self,
        asset: str,
        identifier: str,
        data_type: Literal["media", "text"] = "media",
    ) -> FailedUpload[SampleUpload] | None:
        """
        Process single sample upload with retry logic and error tracking.

        Args:
            asset: MediaAsset to upload or text content
            identifier: Identifier for the sample
            data_type: The type of data being provided. Use "media" for images/videos/audio (default) or "text" for text content.

        Returns:
            FailedUpload describing the failure, or None if the sample uploaded.
        """
        from rapidata.api_client.models.create_sample_endpoint_input import (
            CreateSampleEndpointInput,
        )

        last_exception = None
        for attempt in range(rapidata_config.upload.maxRetries):
            try:
                asset_input = self._asset_uploader.build_asset_input(asset, data_type)

                with suppress_rapidata_error_logging():
                    self._openapi_service.leaderboard.participant_api.participant_participant_id_sample_post(
                        participant_id=self.id,
                        create_sample_endpoint_input=CreateSampleEndpointInput(
                            identifier=identifier,
                            asset=asset_input,
                        ),
                    )

                return None

            except Exception as e:
                last_exception = e
                if attempt < rapidata_config.upload.maxRetries - 1:
                    retry_delay = backoff_delay(attempt)
                    # These attempts are the only record of a transient failure
                    # that later succeeded, so log them at INFO — a flaky link
                    # is diagnosable from a normal run's output.
                    logger.info(
                        "Upload attempt %s/%s failed for %s: %s. Retrying in %.1fs...",
                        attempt + 1,
                        rapidata_config.upload.maxRetries,
                        identifier,
                        last_exception,
                        retry_delay,
                    )
                    time.sleep(retry_delay)

        logger.error(f"Upload failed for {identifier}. Error: {str(last_exception)}")
        return FailedUpload.from_exception(
            SampleUpload(media=asset, identifier=identifier), last_exception
        )

    def upload_media(
        self,
        assets: list[str],
        identifiers: list[str],
        data_type: Literal["media", "text"] = "media",
        max_workers: int | None = None,
    ) -> tuple[list[str], list[FailedUpload[SampleUpload]]]:
        """
        Upload samples concurrently with proper error handling and progress tracking.

        Args:
            assets: List of strings to upload
            identifiers: List of identifiers matching the assets
            data_type: The type of data being provided. Use "media" for images/videos/audio (default) or "text" for text content.
            max_workers: Concurrent upload threads. Defaults to
                `rapidata_config.upload.maxWorkers`. Lower it when the uplink is
                the bottleneck — a saturated connection produces timeouts, not
                throughput.

        Returns:
            tuple[list[str], list[FailedUpload[SampleUpload]]]: The identifiers
            that uploaded, and a `FailedUpload` per sample that did not. Each
            failure carries the media/identifier pair, the reason, and the
            backend trace id. Also available afterwards as `failed_samples`.
        """
        if len(assets) != len(identifiers):
            raise ValueError("Assets and identifiers must have the same length")

        def upload_with_context(
            context: otel_context.Context, asset: str, identifier: str
        ) -> FailedUpload[SampleUpload] | None:
            """Wrapper function that runs _process_single_sample_upload with the provided context."""
            token = otel_context.attach(context)
            try:
                return self._process_single_sample_upload(
                    asset, identifier, data_type=data_type
                )
            finally:
                otel_context.detach(token)

        successful_uploads: list[str] = []
        failed_uploads: list[FailedUpload[SampleUpload]] = []
        total_uploads = len(assets)

        # Capture the current OpenTelemetry context before creating threads
        current_context = otel_context.get_current()

        workers = (
            max_workers
            if max_workers is not None
            else rapidata_config.upload.maxWorkers
        )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    upload_with_context,
                    current_context,
                    asset,
                    identifier,
                ): SampleUpload(media=asset, identifier=identifier)
                for asset, identifier in zip(assets, identifiers)
            }

            with tqdm(
                total=total_uploads,
                desc="Uploading media",
                disable=rapidata_config.logging.silent_mode,
            ) as pbar:
                for future in as_completed(futures):
                    sample = futures[future]
                    try:
                        failure = future.result()
                    except Exception as e:
                        logger.error(f"Future execution failed: {str(e)}")
                        failure = FailedUpload.from_exception(sample, e)

                    if failure is None:
                        successful_uploads.append(sample.identifier)
                    else:
                        failed_uploads.append(failure)

                    pbar.update(1)

        self._failed_samples = failed_uploads
        return successful_uploads, failed_uploads

    def uploaded_identifier_counts(self) -> Counter[str]:
        """Returns how many samples the server holds for each identifier.

        This is server truth, not a client-side tally: it reflects samples that
        actually persisted, including ones whose upload appeared to fail (a
        timeout can arrive after the sample was written).
        """
        with tracer.start_as_current_span(
            "BenchmarkParticipant.uploaded_identifier_counts"
        ):
            counts: Counter[str] = Counter()
            current_page = 1

            while True:
                result = self._openapi_service.leaderboard.sample_api.participant_participant_id_samples_get(
                    participant_id=self.id,
                    page=current_page,
                    page_size=500,
                )

                if result.total_pages is None:
                    raise ValueError(
                        "An error occurred while fetching samples: total_pages is None"
                    )

                for item in result.items:
                    identifier = getattr(item.actual_instance, "identifier", None)
                    if isinstance(identifier, str):
                        counts[identifier] += 1

                if current_page >= result.total_pages:
                    break

                current_page += 1

            return counts

    def _select_missing(
        self, assets: list[str], identifiers: list[str]
    ) -> list[SampleUpload]:
        """Diff the intended samples against what the server actually holds."""
        if len(assets) != len(identifiers):
            raise ValueError("Assets and identifiers must have the same length")

        # A participant may legitimately have several samples for one identifier,
        # so account for the server's samples one at a time rather than by set
        # membership — otherwise a prompt supplied twice looks satisfied by one.
        remaining = self.uploaded_identifier_counts()

        missing: list[SampleUpload] = []
        for asset, identifier in zip(assets, identifiers):
            if remaining[identifier] > 0:
                remaining[identifier] -= 1
            else:
                missing.append(SampleUpload(media=asset, identifier=identifier))

        return missing

    def retry_missing(
        self,
        assets: list[str],
        identifiers: list[str],
        data_type: Literal["media", "text"] = "media",
        max_workers: int | None = None,
    ) -> tuple[list[str], list[FailedUpload[SampleUpload]]]:
        """Upload only the samples the server does not already have.

        Diffs the intended media/identifier pairs against the participant's
        samples on the server and re-uploads just the difference. Verifying
        before re-uploading is what makes this safe to call after a failed run:
        a request can time out *after* the sample was persisted, so retrying
        blindly would give the identifier a second sample and over-weight that
        prompt in matchup sampling.

        Assets that already uploaded are served from the local upload cache, so
        recovering a run is typically far quicker than the original upload.

        Args:
            assets: The full list of media originally intended for the participant.
            identifiers: The identifiers matching the assets.
            data_type: The type of data being provided. Use "media" for images/videos/audio (default) or "text" for text content.
            max_workers: Concurrent upload threads. Defaults to
                `rapidata_config.upload.sweepMaxWorkers`, which is deliberately
                lower than the main pool — failures cluster on saturated links.

        Returns:
            tuple[list[str], list[FailedUpload[SampleUpload]]]: The identifiers
            uploaded by this call, and any that still failed.
        """
        with tracer.start_as_current_span("BenchmarkParticipant.retry_missing"):
            missing = self._select_missing(assets, identifiers)

            if not missing:
                logger.info("All samples are present on the server, nothing to retry")
                self._failed_samples = []
                return [], []

            workers = (
                max_workers
                if max_workers is not None
                else min(
                    rapidata_config.upload.sweepMaxWorkers,
                    rapidata_config.upload.maxWorkers,
                )
            )
            logger.info(
                "Re-uploading %s missing sample(s) with %s worker(s)",
                len(missing),
                workers,
            )

            return self.upload_media(
                [sample.media for sample in missing],
                [sample.identifier for sample in missing],
                data_type=data_type,
                max_workers=workers,
            )
