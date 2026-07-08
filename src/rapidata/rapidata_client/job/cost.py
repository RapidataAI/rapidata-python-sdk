from __future__ import annotations

from dataclasses import dataclass
from time import monotonic, sleep
from typing import Callable, TypeVar, TYPE_CHECKING

from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)
from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError

if TYPE_CHECKING:
    from rapidata.api_client.models.get_job_cost_estimate_endpoint_output import (
        GetJobCostEstimateEndpointOutput,
    )
    from rapidata.api_client.models.get_job_definition_cost_estimate_endpoint_output import (
        GetJobDefinitionCostEstimateEndpointOutput,
    )

T = TypeVar("T")

# The estimate is not priced instantly after a job is created; the endpoint
# answers 409 until it becomes available.
_ESTIMATE_NOT_READY_STATUS = 409
DEFAULT_ESTIMATE_TIMEOUT = 300.0
DEFAULT_ESTIMATE_POLL_INTERVAL = 5.0


@dataclass(frozen=True)
class CostEstimate:
    """An approximate estimate of what a job will cost to run to completion.

    This is an estimate, not the final bill: it is based on a sample of the
    job's tasks and scaled to the total number of responses requested, so the
    amount you are actually charged can differ.

    Attributes:
        estimated_cost: The estimated total cost of running the job to completion.
        datapoint_count: The number of datapoints the job will label.
        required_responses: The total number of responses the job collects to complete.
    """

    estimated_cost: float
    datapoint_count: int
    required_responses: int

    @classmethod
    def _from_model(
        cls,
        model: (
            GetJobCostEstimateEndpointOutput
            | GetJobDefinitionCostEstimateEndpointOutput
        ),
    ) -> CostEstimate:
        return cls(
            estimated_cost=model.estimated_cost,
            datapoint_count=model.datapoint_count,
            required_responses=model.required_responses,
        )


def _poll_for_cost_estimate(
    fetch: Callable[[], T],
    *,
    timeout: float,
    interval: float,
) -> T:
    """Call ``fetch`` until it returns, retrying while the estimate is not ready.

    The estimate endpoints return HTTP 409 until the estimate has been priced.
    That transient status is retried until it becomes available; any other error
    is raised immediately.

    Raises:
        TimeoutError: If the estimate is still not available after ``timeout`` seconds.
    """
    deadline = monotonic() + timeout
    while True:
        try:
            with suppress_rapidata_error_logging():
                return fetch()
        except RapidataError as e:
            if e.status_code != _ESTIMATE_NOT_READY_STATUS:
                raise
            if monotonic() >= deadline:
                raise TimeoutError(
                    f"Cost estimate was not available after {timeout:.0f}s - "
                    "try again shortly."
                ) from e
            logger.debug("Cost estimate not ready yet (409), polling...")
            sleep(interval)
