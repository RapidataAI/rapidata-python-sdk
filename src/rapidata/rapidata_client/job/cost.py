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

# The estimate endpoints answer 409 while the first batch of rapids is still
# being created and priced; once that batch exists the estimate is available.
_ESTIMATE_NOT_READY_STATUS = 409

# The first batch is ~5000 rapids, so the estimate is usually ready within a
# couple of minutes; poll up to this long before giving up.
DEFAULT_ESTIMATE_TIMEOUT = 300.0
DEFAULT_ESTIMATE_POLL_INTERVAL = 5.0


@dataclass(frozen=True)
class CostEstimate:
    """An approximate cost estimate for a job or job definition.

    The estimate is not exact: the backend prices a sample of the rapids that
    have been created so far (the job's first batch) and scales that per-response
    cost up to the total number of responses the job requires. The real cost can
    differ once every rapid has been priced.

    Attributes:
        estimated_cost: The estimated total cost of running to completion.
        cost_per_response: The representative per-response cost the estimate is based on.
        datapoint_count: The number of datapoints in the dataset.
        required_responses: The total number of responses the referee requires to complete.
    """

    estimated_cost: float
    cost_per_response: float
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
            cost_per_response=model.cost_per_response,
            datapoint_count=model.datapoint_count,
            required_responses=model.required_responses,
        )


@dataclass(frozen=True)
class ActualCost:
    """The billed cost of a job, derived from its billing group.

    Attributes:
        net_cost: The billed cost after any discount.
        gross_cost: The cost before any discount.
        response_count: The number of responses attributed to the job.
    """

    net_cost: float
    gross_cost: float
    response_count: int


def _poll_for_cost_estimate(
    fetch: Callable[[], T],
    *,
    timeout: float,
    interval: float,
) -> T:
    """Call ``fetch`` until it returns, polling while the estimate is not ready.

    The estimate endpoints return HTTP 409 while the job's first batch of rapids
    is still being created and priced. That transient status is retried until the
    estimate becomes available; any other error is raised immediately.

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
                    "Cost estimate was not available after "
                    f"{timeout:.0f}s. The job's rapids may still be getting "
                    "created and priced - try again shortly."
                ) from e
            logger.debug("Cost estimate not ready yet (409), polling...")
            sleep(interval)
