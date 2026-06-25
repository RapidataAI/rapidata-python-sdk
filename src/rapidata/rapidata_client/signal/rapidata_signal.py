from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic, sleep
from typing import TYPE_CHECKING, Union

from rapidata.rapidata_client.config import logger, managed_print, tracer
from rapidata.rapidata_client.signal.signal_run import SignalRun

if TYPE_CHECKING:
    from rapidata.api_client.models.get_signal_by_id_endpoint_output import (
        GetSignalByIdEndpointOutput,
    )
    from rapidata.api_client.models.query_signals_endpoint_output import (
        QuerySignalsEndpointOutput,
    )
    from rapidata.service.openapi_service import OpenAPIService

    SignalOutput = Union[GetSignalByIdEndpointOutput, QuerySignalsEndpointOutput]


class RapidataSignal:
    """An instance of a Rapidata signal.

    A signal runs an audience job creation on a recurring schedule. Each run produces a
    :class:`SignalRun` that wraps the audience job that was created (or an explanation
    of why the run was skipped or failed). Use the manager (:py:attr:`RapidataClient.signals`)
    to create or look up signals; use the instance methods on this class to manage an
    existing signal's lifecycle and observe its runs.
    """

    def __init__(
        self,
        openapi_service: OpenAPIService,
        data: SignalOutput,
    ):
        self._openapi_service = openapi_service
        self._apply(data)
        logger.debug("RapidataSignal initialized: %s", self.id)

    def _apply(self, data: SignalOutput) -> None:
        """Replace this instance's cached state with the latest API payload."""
        self._id: str = data.id
        self._name: str = data.name
        self._description: str | None = data.description
        self._audience_id: str = data.audience_id
        self._job_definition_id: str = data.job_definition_id
        self._revision_number: int | None = data.revision_number
        self._interval_seconds: int = data.interval_seconds
        self._next_run_at: datetime = data.next_run_at
        self._last_run_at: datetime | None = data.last_run_at
        self._is_paused: bool = data.is_paused
        self._is_public: bool = data.is_public
        self._created_at: datetime = data.created_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def audience_id(self) -> str:
        return self._audience_id

    @property
    def job_definition_id(self) -> str:
        return self._job_definition_id

    @property
    def revision_number(self) -> int | None:
        return self._revision_number

    @property
    def interval_seconds(self) -> int:
        return self._interval_seconds

    @property
    def next_run_at(self) -> datetime:
        return self._next_run_at

    @property
    def last_run_at(self) -> datetime | None:
        return self._last_run_at

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_public(self) -> bool:
        return self._is_public

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def refresh(self) -> RapidataSignal:
        """Re-fetch this signal from the server and update local state.

        Returns:
            RapidataSignal: ``self`` for chaining.
        """
        with tracer.start_as_current_span("RapidataSignal.refresh"):
            data = self._openapi_service.signal.signal_api.signal_signal_id_get(self.id)
            self._apply(data)
            return self

    def pause(self) -> RapidataSignal:
        """Pause the signal. Scheduled runs stop until :py:meth:`resume` is called.

        Returns:
            RapidataSignal: ``self`` for chaining.
        """
        with tracer.start_as_current_span("RapidataSignal.pause"):
            logger.info("Pausing signal '%s'", self.id)
            self._openapi_service.signal.signal_api.signal_signal_id_pause_post(self.id)
            self.refresh()
            managed_print(f"Signal '{self}' has been paused.")
            return self

    def resume(self) -> RapidataSignal:
        """Resume a paused signal. Scheduled runs start firing again at the configured interval.

        Returns:
            RapidataSignal: ``self`` for chaining.
        """
        with tracer.start_as_current_span("RapidataSignal.resume"):
            logger.info("Resuming signal '%s'", self.id)
            self._openapi_service.signal.signal_api.signal_signal_id_resume_post(
                self.id
            )
            self.refresh()
            managed_print(f"Signal '{self}' has been resumed.")
            return self

    def delete(self) -> None:
        """Delete the signal. Existing runs and their audience jobs are unaffected."""
        with tracer.start_as_current_span("RapidataSignal.delete"):
            logger.info("Deleting signal '%s'", self.id)
            self._openapi_service.signal.signal_api.signal_signal_id_delete(self.id)
            managed_print(f"Signal '{self}' has been deleted.")

    def trigger(self) -> None:
        """Trigger the signal manually, creating one extra run outside the schedule.

        The run is created asynchronously; use :py:meth:`wait_for_next_run` to block
        until it appears and reaches a terminal status.
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
        interval_seconds: int | None = None,
    ) -> RapidataSignal:
        """Update mutable fields on the signal.

        Args:
            name: New display name. Omit to leave unchanged.
            description: New description. Omit to leave unchanged.
            interval_seconds: New scheduling interval. Omit to leave unchanged.

        Returns:
            RapidataSignal: ``self``, refreshed with the server's response.
        """
        if name is None and description is None and interval_seconds is None:
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
                    intervalSeconds=interval_seconds,
                ),
            )
            self.refresh()
            return self

    def get_runs(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_descending: bool = True,
    ) -> list[SignalRun]:
        """List historical runs of this signal.

        Args:
            page: 1-indexed page number.
            page_size: Number of runs per page.
            sort_descending: When ``True`` (default), newest runs come first.

        Returns:
            list[SignalRun]: The runs on the requested page.
        """
        with tracer.start_as_current_span("RapidataSignal.get_runs"):
            result = self._openapi_service.signal.signal_api.signal_signal_id_run_get(
                self.id,
                page=page,
                page_size=page_size,
                sort=["-started_at" if sort_descending else "started_at"],
            )
            return [SignalRun._from_api(item) for item in result.items]

    def get_run(self, run_id: str) -> SignalRun:
        """Get a specific run by ID.

        Args:
            run_id: The ID of the run to fetch.

        Returns:
            SignalRun: The requested run.
        """
        with tracer.start_as_current_span("RapidataSignal.get_run"):
            data = self._openapi_service.signal.signal_api.signal_run_run_id_get(run_id)
            return SignalRun._from_api(data)

    def wait_for_next_run(
        self,
        timeout: float = 300,
        poll_interval: float = 5.0,
    ) -> SignalRun:
        """Block until the next run of this signal reaches a terminal status.

        Polls the signal's runs and waits for any run that started *after* this call was
        made to reach a terminal status (``Completed``, ``Failed``, or ``Skipped``).
        Useful after :py:meth:`trigger` or when watching a scheduled run come through.

        Args:
            timeout: Maximum seconds to wait. Raises :py:class:`TimeoutError` on expiry.
            poll_interval: Seconds between polls.

        Returns:
            SignalRun: The first new run to reach a terminal status.

        Raises:
            TimeoutError: If no new terminal run is observed within ``timeout`` seconds.
        """
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")

        with tracer.start_as_current_span("RapidataSignal.wait_for_next_run"):
            started_waiting = datetime.now(timezone.utc)
            deadline = monotonic() + timeout

            logger.info(
                "Waiting up to %.0fs for the next terminal run of signal '%s'",
                timeout,
                self.id,
            )
            while True:
                # Pull the most recent runs and look for any whose started_at is after we
                # began waiting AND that has reached a terminal status. We re-look every
                # poll because a Pending run may transition while we wait.
                runs = self.get_runs(page=1, page_size=20, sort_descending=True)
                candidates = [r for r in runs if r.started_at >= started_waiting]
                terminal = [r for r in candidates if r.is_terminal]
                if terminal:
                    # `runs` came back descending, so the last terminal in the list is
                    # the earliest new terminal — return that one (the next to finish).
                    return terminal[-1]

                if monotonic() >= deadline:
                    raise TimeoutError(
                        f"No new terminal run of signal '{self.id}' within {timeout} seconds."
                    )
                sleep(poll_interval)

    def __str__(self) -> str:
        return f"RapidataSignal(name='{self.name}', id='{self.id}')"

    def __repr__(self) -> str:
        return self.__str__()
