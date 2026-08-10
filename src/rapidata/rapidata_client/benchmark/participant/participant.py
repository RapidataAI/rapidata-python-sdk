from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
import time
from typing import Any, Literal
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

# The backend rejects anything above its MaxPageSize (100) outright rather than
# clamping, so this is a hard ceiling and not a tuning knob.
_SAMPLES_PAGE_SIZE = 100

# http / https in any case — same detection the asset uploader uses to tell a
# remote URL from a local path.
_URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)


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

    @property
    def status(self) -> ParticipantStatus:
        """The current status of the participant."""
        return self._status

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
    ) -> tuple[list[str], list[FailedUpload[SampleUpload]]]:
        """
        Upload samples concurrently with proper error handling and progress tracking.

        Args:
            assets: List of strings to upload
            identifiers: List of identifiers matching the assets
            data_type: The type of data being provided. Use "media" for images/videos/audio (default) or "text" for text content.

        Returns:
            tuple[list[str], list[FailedUpload[SampleUpload]]]: The identifiers
            that uploaded, and a `FailedUpload` per sample that did not. Each
            failure carries the media/identifier pair, the reason, and the
            backend trace id.
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

        with ThreadPoolExecutor(
            max_workers=rapidata_config.upload.maxWorkers
        ) as executor:
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

        return successful_uploads, failed_uploads

    @staticmethod
    def _local_asset_key(asset: str, data_type: Literal["media", "text"]) -> str:
        """The form a local asset takes once the server reports it back.

        Remote URLs round-trip verbatim as `sourceUrl`; local files come back as
        the bare `originalFilename`, so the directory part is dropped here to
        match. Mirrors the normalization `RapidataBenchmark` already applies to
        prompt assets.
        """
        if data_type == "text" or _URL_SCHEME_RE.match(asset):
            return asset

        return os.path.basename(asset)

    @staticmethod
    def _server_asset_key(asset: Any) -> str | None:
        """The comparable form of a sample's asset as the server reports it.

        Returns None when the asset is a shape this cannot read (a multi-asset,
        or metadata the backend has stopped sending); callers must treat that as
        "unidentifiable", never as "absent".
        """
        instance = getattr(asset, "actual_instance", None)

        text = getattr(instance, "text", None)
        if isinstance(text, str):
            return text

        metadata = getattr(instance, "metadata", None)
        if not isinstance(metadata, dict):
            return None

        source_url = getattr(
            getattr(metadata.get("sourceUrl"), "actual_instance", None), "url", None
        )
        if isinstance(source_url, str):
            return source_url

        original_filename = getattr(
            getattr(metadata.get("originalFilename"), "actual_instance", None),
            "original_filename",
            None,
        )
        if isinstance(original_filename, str):
            return original_filename

        return None

    def _uploaded_sample_keys(self) -> Counter[tuple[str, str | None]]:
        """Counts the samples the server holds, per (identifier, asset).

        This is server truth, not a client-side tally: it reflects samples that
        actually persisted, including ones whose upload appeared to fail (a
        timeout can arrive after the sample was written).
        """
        with tracer.start_as_current_span("BenchmarkParticipant._uploaded_sample_keys"):
            counts: Counter[tuple[str, str | None]] = Counter()
            current_page = 1

            while True:
                result = self._openapi_service.leaderboard.sample_api.participant_participant_id_samples_get(
                    participant_id=self.id,
                    page=current_page,
                    page_size=_SAMPLES_PAGE_SIZE,
                )

                if result.total_pages is None:
                    raise ValueError(
                        "An error occurred while fetching samples: total_pages is None"
                    )

                for item in result.items:
                    sample = item.actual_instance
                    identifier = getattr(sample, "identifier", None)
                    if isinstance(identifier, str):
                        key = self._server_asset_key(getattr(sample, "asset", None))
                        counts[(identifier, key)] += 1

                if current_page >= result.total_pages:
                    break

                current_page += 1

            return counts

    def missing_samples(
        self,
        assets: list[str],
        identifiers: list[str],
        data_type: Literal["media", "text"] = "media",
    ) -> list[SampleUpload]:
        """Returns the intended samples the server does not hold yet.

        Answers "what still needs uploading" by asking the server, so it stays
        correct on any participant — including one fetched from
        ``benchmark.participants`` rather than freshly uploaded to.

        Matching is per media *and* identifier, not per identifier alone: an
        identifier may carry several distinct assets, and knowing only that one
        of three landed says nothing about which one. The one case this cannot
        separate is two different paths sharing a filename under the same
        identifier (`a/1.png` and `b/1.png`) — they are indistinguishable once
        the server has reduced them to `originalFilename`.

        Args:
            assets: The full list of media intended for the participant.
            identifiers: The identifiers matching the assets.
            data_type: The type of data being provided. Use "media" for images/videos/audio (default) or "text" for text content.
        """
        if len(assets) != len(identifiers):
            raise ValueError("Assets and identifiers must have the same length")

        # Decrement rather than test membership: the same media may legitimately
        # be supplied more than once for an identifier, and each occurrence needs
        # its own sample.
        remaining = self._uploaded_sample_keys()

        missing: list[SampleUpload] = []
        for asset, identifier in zip(assets, identifiers):
            key = (identifier, self._local_asset_key(asset, data_type))
            unreadable = (identifier, None)

            if remaining[key] > 0:
                remaining[key] -= 1
            elif remaining[unreadable] > 0:
                # A sample exists whose asset could not be read back. Spend it
                # here rather than re-upload: a duplicate sample silently
                # over-weights the prompt, while a missing one is reported.
                remaining[unreadable] -= 1
            else:
                missing.append(SampleUpload(media=asset, identifier=identifier))

        return missing

    def retry_missing(
        self,
        assets: list[str],
        identifiers: list[str],
        data_type: Literal["media", "text"] = "media",
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

        Returns:
            tuple[list[str], list[FailedUpload[SampleUpload]]]: The identifiers
            uploaded by this call, and any that still failed.
        """
        with tracer.start_as_current_span("BenchmarkParticipant.retry_missing"):
            missing = self.missing_samples(assets, identifiers, data_type=data_type)

            if not missing:
                logger.info("All samples are present on the server, nothing to retry")
                return [], []

            logger.info("Re-uploading %s missing sample(s)", len(missing))

            return self.upload_media(
                [sample.media for sample in missing],
                [sample.identifier for sample in missing],
                data_type=data_type,
            )
