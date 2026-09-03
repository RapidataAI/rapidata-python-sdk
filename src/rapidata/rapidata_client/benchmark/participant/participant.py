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
from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError


from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.participant_status import ParticipantStatus

# The backend rejects anything above its MaxPageSize (100) outright rather than
# clamping, so this is a hard ceiling and not a tuning knob.
_SAMPLES_PAGE_SIZE = 100

# Returned when the participant already holds this sample. The only conflict the
# sample endpoint raises, so the status alone identifies it.
_ALREADY_EXISTS_STATUS = 409


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

        If the benchmark requires a minimum number of samples per prompt, any
        prompt this participant filled with fewer than that many samples is
        logged as a warning. The submission still goes through — the check is
        advisory, not a rejection.
        """
        from rapidata.api_client.models.submit_participants_endpoint_input import (
            SubmitParticipantsEndpointInput,
        )

        with tracer.start_as_current_span("BenchmarkParticipant.run"):
            # Submitted through the batch endpoint as a batch of one: only its response
            # carries the min-assets-per-prompt warning, and for a single participant this
            # is equivalent to the per-participant submit.
            result = self._openapi_service.leaderboard.participant_api.participants_submit_post(
                SubmitParticipantsEndpointInput(participantIds=[self.id])
            )
            self._status = ParticipantStatus.SUBMITTED

            warning = result.min_assets_per_prompt_warning
            if warning is not None:
                shortfalls = [
                    prompt
                    for participant in warning.underfilled_participants
                    for prompt in participant.underfilled_prompts
                ]
                if shortfalls:
                    details = ", ".join(
                        f"'{prompt.identifier}' ({prompt.asset_count}/{warning.min_assets_per_prompt})"
                        for prompt in shortfalls
                    )
                    logger.warning(
                        "Participant '%s' submitted with %d prompt(s) below the benchmark's "
                        "required %d samples per prompt: %s. Add more versions or remove these "
                        "prompts to avoid skewed comparisons.",
                        self.name,
                        len(shortfalls),
                        warning.min_assets_per_prompt,
                        details,
                    )

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

            except RapidataError as e:
                if e.status_code == _ALREADY_EXISTS_STATUS:
                    # The backend rejects a sample the participant already holds for
                    # this identifier and asset. That is the success case for a retry:
                    # the sample we wanted is there, and re-sending would double the
                    # prompt's weight in matchup sampling.
                    logger.debug("Sample already present for %s", identifier)
                    return None

                last_exception = e
                if attempt < rapidata_config.upload.maxRetries - 1:
                    retry_delay = backoff_delay(attempt)
                    logger.info(
                        "Upload attempt %s/%s failed for %s: %s. Retrying in %.1fs...",
                        attempt + 1,
                        rapidata_config.upload.maxRetries,
                        identifier,
                        last_exception,
                        retry_delay,
                    )
                    time.sleep(retry_delay)

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

        # Not the last word on this sample: callers sweep with `retry_missing` and then
        # report whatever is still short, so an error here double-counts recoveries.
        logger.info("Upload failed for %s. Error: %s", identifier, last_exception)
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

    def _uploaded_identifier_counts(self) -> Counter[str]:
        """Counts the samples the server holds for each identifier.

        Server truth, not a client-side tally: it reflects samples that actually
        persisted, including ones whose upload appeared to fail because the
        response never arrived.
        """
        with tracer.start_as_current_span(
            "BenchmarkParticipant._uploaded_identifier_counts"
        ):
            counts: Counter[str] = Counter()
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
                    identifier = getattr(item.actual_instance, "identifier", None)
                    if isinstance(identifier, str):
                        counts[identifier] += 1

                if current_page >= result.total_pages:
                    break

                current_page += 1

            return counts

    def missing_counts(self, identifiers: list[str]) -> Counter[str]:
        """Returns how many samples each identifier is still short on the server.

        Identifiers that are fully uploaded are absent from the result, so an
        empty counter means nothing is outstanding. Being a server-side question,
        it is answered correctly for any participant — including one fetched from
        ``benchmark.participants`` rather than freshly uploaded to.

        Args:
            identifiers: The full list of identifiers intended for the participant.
        """
        intended = Counter(identifiers)
        intended.subtract(self._uploaded_identifier_counts())

        return Counter({k: v for k, v in intended.items() if v > 0})

    def retry_missing(
        self,
        assets: list[str],
        identifiers: list[str],
        data_type: Literal["media", "text"] = "media",
    ) -> tuple[list[str], list[FailedUpload[SampleUpload]]]:
        """Upload the samples the server is still missing.

        Asks the server which identifiers are short, then re-sends every asset
        belonging to those identifiers. The backend rejects any sample the
        participant already holds, so the ones that did land are skipped without
        being duplicated — which is what makes this safe to call repeatedly. It
        also means the client never has to work out *which* asset of an identifier
        is the missing one; the server decides.

        Assets that already uploaded are served from the local upload cache, so
        recovering a run is typically far quicker than the original upload.

        Args:
            assets: The full list of media originally intended for the participant.
            identifiers: The identifiers matching the assets.
            data_type: The type of data being provided. Use "media" for images/videos/audio (default) or "text" for text content.

        Returns:
            tuple[list[str], list[FailedUpload[SampleUpload]]]: The identifiers
            uploaded across all rounds, and any that still failed on the last one.
        """
        if len(assets) != len(identifiers):
            raise ValueError("Assets and identifiers must have the same length")

        with tracer.start_as_current_span("BenchmarkParticipant.retry_missing"):
            successful: list[str] = []
            failed: list[FailedUpload[SampleUpload]] = []

            for _ in range(rapidata_config.upload.maxRetries):
                short = self.missing_counts(identifiers)
                if not short:
                    break

                outstanding = sum(short.values())
                logger.info(
                    "%s sample(s) missing across %s identifier(s); re-uploading",
                    outstanding,
                    len(short),
                )

                pairs = [
                    (asset, identifier)
                    for asset, identifier in zip(assets, identifiers)
                    if identifier in short
                ]

                round_successful, failed = self.upload_media(
                    [asset for asset, _ in pairs],
                    [identifier for _, identifier in pairs],
                    data_type=data_type,
                )
                successful.extend(round_successful)

                # Stop once a round stops closing the gap, so a sample the server
                # keeps refusing cannot spin here.
                if sum(self.missing_counts(identifiers).values()) >= outstanding:
                    break

            return successful, failed
