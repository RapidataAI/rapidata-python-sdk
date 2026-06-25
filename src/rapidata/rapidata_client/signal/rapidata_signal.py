from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic, sleep
from typing import TYPE_CHECKING, Union

from rapidata.rapidata_client.config import logger, managed_print, tracer

if TYPE_CHECKING:
    from rapidata.api_client.models.get_signal_by_id_endpoint_output import (
        GetSignalByIdEndpointOutput,
    )
    from rapidata.api_client.models.query_signals_endpoint_output import (
        QuerySignalsEndpointOutput,
    )
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob
    from rapidata.service.openapi_service import OpenAPIService

    SignalOutput = Union[GetSignalByIdEndpointOutput, QuerySignalsEndpointOutput]


class RapidataSignal:
    """A live handle to a Rapidata signal.

    A signal creates one audience job on a recurring schedule — every interval tick
    spawns a :class:`RapidataJob` built from the signal's job definition and audience.
    Use the manager (:py:attr:`RapidataClient.signals`) to create or look up signals;
    use the methods here to control a signal and reach the jobs it produces.

    This is a *live* handle: identity fields (``id``, ``audience_id``,
    ``job_definition_id``, ``created_at`` …) are fixed at creation, while mutable state
    (``name``, ``is_paused``, ``next_run_at`` …) is re-fetched from the server on every
    access so it never goes stale.
    """

    def __init__(
        self,
        openapi_service: OpenAPIService,
        data: SignalOutput,
    ):
        self._openapi_service = openapi_service
        # Identity / immutable fields — safe to cache for the object's lifetime.
        self.id: str = data.id
        self.audience_id: str = data.audience_id
        self.job_definition_id: str = data.job_definition_id
        self.revision_number: int | None = data.revision_number
        self.is_public: bool = data.is_public
        self.created_at: datetime = data.created_at
        # Last-known name, kept only as a display label for __str__/logging; the `name`
        # property always reads the live value.
        self._name: str = data.name
        logger.debug("RapidataSignal initialized: %s", self.id)

    def _latest(self) -> GetSignalByIdEndpointOutput:
        """Fetch the current server-side state of this signal."""
        return self._openapi_service.signal.signal_api.signal_signal_id_get(self.id)

    @property
    def name(self) -> str:
        return self._latest().name

    @property
    def description(self) -> str | None:
        return self._latest().description

    @property
    def interval_hours(self) -> float:
        return self._latest().interval_seconds / 3600

    @property
    def next_run_at(self) -> datetime:
        return self._latest().next_run_at

    @property
    def last_run_at(self) -> datetime | None:
        return self._latest().last_run_at

    @property
    def is_paused(self) -> bool:
        return self._latest().is_paused

    def pause(self) -> RapidataSignal:
        """Pause the signal. Scheduled jobs stop until :py:meth:`resume` is called.

        Returns:
            RapidataSignal: ``self`` for chaining.
        """
        with tracer.start_as_current_span("RapidataSignal.pause"):
            logger.info("Pausing signal '%s'", self.id)
            self._openapi_service.signal.signal_api.signal_signal_id_pause_post(self.id)
            managed_print(f"Signal '{self}' has been paused.")
            return self

    def resume(self) -> RapidataSignal:
        """Resume a paused signal. Scheduled jobs start firing again at the configured interval.

        Returns:
            RapidataSignal: ``self`` for chaining.
        """
        with tracer.start_as_current_span("RapidataSignal.resume"):
            logger.info("Resuming signal '%s'", self.id)
            self._openapi_service.signal.signal_api.signal_signal_id_resume_post(
                self.id
            )
            managed_print(f"Signal '{self}' has been resumed.")
            return self

    def delete(self) -> None:
        """Delete the signal. Jobs it already created are unaffected."""
        with tracer.start_as_current_span("RapidataSignal.delete"):
            logger.info("Deleting signal '%s'", self.id)
            self._openapi_service.signal.signal_api.signal_signal_id_delete(self.id)
            managed_print(f"Signal '{self}' has been deleted.")

    def trigger(self) -> None:
        """Trigger the signal manually, creating one extra job outside the schedule.

        The job is created asynchronously; use :py:meth:`wait_for_next_job` to block
        until it appears.
        """
        with tracer.start_as_current_span("RapidataSignal.trigger"):
            logger.info("Triggering signal '%s'", self.id)
            self._openapi_service.signal.signal_api.signal_signal_id_trigger_post(
                self.id
            )

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        interval_hours: float | None = None,
    ) -> RapidataSignal:
        """Update mutable fields on the signal.

        Args:
            name: New display name. Omit to leave unchanged.
            description: New description. Omit to leave unchanged.
            interval_hours: New scheduling interval, in hours. Omit to leave unchanged.

        Returns:
            RapidataSignal: ``self`` for chaining.
        """
        if name is None and description is None and interval_hours is None:
            # Nothing requested — avoid a useless round trip.
            return self

        from rapidata.api_client.models.update_signal_endpoint_input import (
            UpdateSignalEndpointInput,
        )

        with tracer.start_as_current_span("RapidataSignal.update"):
            self._openapi_service.signal.signal_api.signal_signal_id_patch(
                self.id,
                UpdateSignalEndpointInput(
                    name=name,
                    description=description,
                    intervalSeconds=(
                        None if interval_hours is None else round(interval_hours * 3600)
                    ),
                ),
            )
            if name is not None:
                self._name = name
            return self

    def get_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_descending: bool = True,
    ) -> list[RapidataJob]:
        """List the jobs this signal has created (newest first by default).

        Each scheduled or manual firing that spawned a job is returned as a live
        :class:`RapidataJob`. Firings that were skipped without creating a job are
        not included.

        Args:
            page: 1-indexed page number.
            page_size: Number of firings to inspect per page.
            sort_descending: When ``True`` (default), newest jobs come first.

        Returns:
            list[RapidataJob]: The jobs on the requested page.
        """
        from rapidata.rapidata_client.job.rapidata_job_manager import (
            RapidataJobManager,
        )

        with tracer.start_as_current_span("RapidataSignal.get_jobs"):
            runs = self._openapi_service.signal.signal_api.signal_signal_id_run_get(
                self.id,
                page=page,
                page_size=page_size,
                sort=["-started_at" if sort_descending else "started_at"],
            ).items
            job_manager = RapidataJobManager(openapi_service=self._openapi_service)
            return [
                job_manager.get_job_by_id(run.audience_job_id)
                for run in runs
                if run.audience_job_id
            ]

    def wait_for_next_job(
        self,
        timeout: float = 300,
        poll_interval: float = 5.0,
    ) -> RapidataJob:
        """Block until the signal's next firing creates a job, then return it.

        Waits for a firing that started *after* this call and has spawned a job
        (skipped firings are ignored). Handy right after :py:meth:`trigger`. The
        returned :class:`RapidataJob` is live — call ``get_results()`` or
        ``display_progress_bar()`` on it to follow the job to completion.

        Args:
            timeout: Maximum seconds to wait. Raises :py:class:`TimeoutError` on expiry.
            poll_interval: Seconds between polls.

        Returns:
            RapidataJob: The job created by the next firing.

        Raises:
            TimeoutError: If no new job is created within ``timeout`` seconds.
        """
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")

        from rapidata.rapidata_client.job.rapidata_job_manager import (
            RapidataJobManager,
        )

        with tracer.start_as_current_span("RapidataSignal.wait_for_next_job"):
            started_waiting = datetime.now(timezone.utc)
            deadline = monotonic() + timeout
            job_manager = RapidataJobManager(openapi_service=self._openapi_service)

            logger.info(
                "Waiting up to %.0fs for the next job of signal '%s'",
                timeout,
                self.id,
            )
            while True:
                runs = self._openapi_service.signal.signal_api.signal_signal_id_run_get(
                    self.id, page=1, page_size=20, sort=["-started_at"]
                ).items
                # Newest-first, so the last match is the earliest new firing with a job.
                fresh_job_ids = [
                    run.audience_job_id
                    for run in runs
                    if run.started_at >= started_waiting and run.audience_job_id
                ]
                if fresh_job_ids:
                    return job_manager.get_job_by_id(fresh_job_ids[-1])

                if monotonic() >= deadline:
                    raise TimeoutError(
                        f"No new job from signal '{self.id}' within {timeout} seconds."
                    )
                sleep(poll_interval)

    def __str__(self) -> str:
        return f"RapidataSignal(name='{self._name}', id='{self.id}')"

    def __repr__(self) -> str:
        return self.__str__()
