from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.signal.rapidata_signal import RapidataSignal
from rapidata.rapidata_client.signal.signal_run import SignalRun

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService


class RapidataSignalManager:
    """Manage signals: schedules that periodically create audience jobs.

    A signal binds an audience to a job definition and an interval. The signal service
    creates one audience job per interval tick (a :class:`SignalRun`). Use this manager
    to create, look up, and find signals; use methods on the returned
    :class:`RapidataSignal` to control a specific signal and observe its runs.

    Access this manager via :py:attr:`RapidataClient.signals`.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        logger.debug("RapidataSignalManager initialized")

    def create_signal(
        self,
        name: str,
        audience_id: str,
        job_definition_id: str,
        interval_hours: float,
        description: str | None = None,
        revision_number: int | None = None,
        is_public: bool = False,
    ) -> RapidataSignal:
        """Create a new signal.

        Args:
            name: Display name for the signal.
            audience_id: ID of the audience the signal targets each run.
            job_definition_id: ID of the job definition that backs each run.
            interval_hours: How often the signal fires, in hours.
            description: Optional human-readable description.
            revision_number: Optional explicit revision of ``job_definition_id`` to pin
                this signal to. If omitted, the signal follows the latest revision.
            is_public: Whether other users can discover and read this signal.

        Returns:
            RapidataSignal: The created signal.
        """
        if interval_hours <= 0:
            raise ValueError("interval_hours must be positive")

        from rapidata.api_client.models.create_signal_endpoint_input import (
            CreateSignalEndpointInput,
        )

        with tracer.start_as_current_span("RapidataSignalManager.create_signal"):
            logger.debug(
                "Creating signal '%s' (audience=%s, job_definition=%s, interval=%sh)",
                name,
                audience_id,
                job_definition_id,
                interval_hours,
            )
            created = self._openapi_service.signal.signal_api.signal_post(
                CreateSignalEndpointInput(
                    name=name,
                    description=description,
                    audienceId=audience_id,
                    jobDefinitionId=job_definition_id,
                    revisionNumber=revision_number,
                    intervalSeconds=round(interval_hours * 3600),
                    isPublic=is_public,
                )
            )
            # The create endpoint only echoes the id; fetch the full signal to populate.
            return self.get_signal_by_id(created.id)

    def get_signal_by_id(self, signal_id: str) -> RapidataSignal:
        """Get a signal by ID.

        Args:
            signal_id: The signal to fetch.

        Returns:
            RapidataSignal: The signal.
        """
        with tracer.start_as_current_span("RapidataSignalManager.get_signal_by_id"):
            data = self._openapi_service.signal.signal_api.signal_signal_id_get(
                signal_id
            )
            return RapidataSignal(self._openapi_service, data)

    def find_signals(
        self,
        name: str = "",
        amount: int = 10,
        page: int = 1,
    ) -> list[RapidataSignal]:
        """Find signals visible to you (your own signals plus public ones).

        Args:
            name: Filter signals by name (matching signals will contain this string).
                Defaults to "" for any signal.
            amount: The maximum number of signals to return. Defaults to 10.
            page: The page of signals to return. Defaults to 1.

        Returns:
            list[RapidataSignal]: The matching signals.
        """
        from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
            AudienceAudienceIdJobsGetJobIdParameter,
        )

        with tracer.start_as_current_span("RapidataSignalManager.find_signals"):
            logger.debug("Finding signals: %s, %s", name, amount)
            result = self._openapi_service.signal.signal_api.signal_get(
                page=page,
                page_size=amount,
                name=AudienceAudienceIdJobsGetJobIdParameter(contains=name),
                sort=["-created_at"],
            )
            return [
                RapidataSignal(self._openapi_service, item) for item in result.items
            ]

    def get_run_by_id(self, run_id: str) -> SignalRun:
        """Get a single signal run by ID, when the signal it belongs to is unknown.

        Args:
            run_id: The run ID.

        Returns:
            SignalRun: The run.
        """
        with tracer.start_as_current_span("RapidataSignalManager.get_run_by_id"):
            data = self._openapi_service.signal.signal_api.signal_run_run_id_get(run_id)
            return SignalRun._from_api(data)

    def __str__(self) -> str:
        return "RapidataSignalManager"

    def __repr__(self) -> str:
        return self.__str__()
