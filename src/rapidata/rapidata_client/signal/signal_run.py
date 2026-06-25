from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Union

if TYPE_CHECKING:
    from rapidata.api_client.models.get_signal_run_by_id_endpoint_output import (
        GetSignalRunByIdEndpointOutput,
    )
    from rapidata.api_client.models.query_signal_runs_endpoint_output import (
        QuerySignalRunsEndpointOutput,
    )

    SignalRunOutput = Union[
        GetSignalRunByIdEndpointOutput, QuerySignalRunsEndpointOutput
    ]

SignalRunStatus = Literal["Pending", "Running", "Completed", "Failed", "Skipped"]
SignalRunTriggerSource = Literal["Scheduled", "Manual"]
_TERMINAL_STATUSES: frozenset[str] = frozenset({"Completed", "Failed", "Skipped"})


@dataclass(frozen=True)
class SignalRun:
    """A single execution of a Signal — the result of one audience job creation.

    A run is created either by the signal's scheduled interval or by an explicit
    :py:meth:`RapidataSignal.trigger` call. It transitions through statuses until
    it reaches a terminal one (``Completed``, ``Failed`` or ``Skipped``).
    """

    id: str
    signal_id: str
    trigger_source: SignalRunTriggerSource
    started_at: datetime
    status: SignalRunStatus
    audience_job_id: str | None
    completed_at: datetime | None
    result_file_name: str | None
    failure_message: str | None
    skipped_reason: str | None

    @property
    def is_terminal(self) -> bool:
        """True when the run has finished (``Completed``, ``Failed`` or ``Skipped``)."""
        return self.status in _TERMINAL_STATUSES

    @property
    def succeeded(self) -> bool:
        """True when the run finished successfully (``Completed``)."""
        return self.status == "Completed"

    @classmethod
    def _from_api(cls, model: SignalRunOutput) -> SignalRun:
        """Build a SignalRun from a signal-service run model."""
        return cls(
            id=model.id,
            signal_id=model.signal_id,
            trigger_source=model.trigger_source.value,
            started_at=model.started_at,
            status=model.status.value,
            audience_job_id=model.audience_job_id,
            completed_at=model.completed_at,
            result_file_name=model.result_file_name,
            failure_message=model.failure_message,
            skipped_reason=model.skipped_reason,
        )

    def __str__(self) -> str:
        return f"SignalRun(id='{self.id}', status='{self.status}')"
