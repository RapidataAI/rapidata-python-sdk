from __future__ import annotations

import json
import urllib.parse
import webbrowser
from datetime import datetime
from time import sleep
from typing import Callable, TypeVar, TYPE_CHECKING
from colorama import Fore
from tqdm.auto import tqdm

from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import (
    logger,
    managed_print,
    rapidata_config,
    tracer,
)
from rapidata.rapidata_client.api.rapidata_api_client import (
    suppress_rapidata_error_logging,
)
from rapidata.rapidata_client.job.cost import (
    ActualCost,
    CostEstimate,
    DEFAULT_ESTIMATE_POLL_INTERVAL,
    DEFAULT_ESTIMATE_TIMEOUT,
    _poll_for_cost_estimate,
)

if TYPE_CHECKING:
    from rapidata.rapidata_client.results.rapidata_results import RapidataResults

T = TypeVar("T")


class RapidataJob:
    """
    An instance of a Rapidata job.

    Used to interact with a specific job in the Rapidata system, such as getting
    status and retrieving results.

    A job is created from a job definition and an audience, and represents a
    specific run of that definition.

    Args:
        job_id: The ID of the job.
        name: The name of the job.
        openapi_service: The OpenAPIService instance for API interaction.
    """

    def __init__(
        self,
        job_id: str,
        name: str,
        audience_id: str,
        created_at: datetime,
        definition_id: str,
        openapi_service: OpenAPIService,
        pipeline_id: str | None = None,
    ):
        self.id = job_id
        self.name = name
        self.audience_id = audience_id
        self._openapi_service = openapi_service
        self.created_at = created_at
        self.definition_id = definition_id
        self.__pipeline_id = pipeline_id
        self.__completed_at = None
        self.__estimated_cost: CostEstimate | None = None
        self.job_details_page = f"https://app.{self._openapi_service.environment}/audiences/{self.audience_id}/job/{self.id}"
        logger.debug("RapidataJob initialized")

    def _get_job_failure_message(self) -> str | None:
        """Retrieves the failure message from the job if available."""
        try:
            job = self._openapi_service.order.job_api.job_job_id_get(self.id)
            return job.failure_message
        except Exception:
            logger.debug("Failed to get job failure message", self, exc_info=True)
            return None

    def _retry_operation(
        self,
        operation: Callable[[], T],
        max_retries: int = 10,
        retry_delay: float = 2,
    ) -> T:
        """
        Unified retry logic for all operations with failure message handling.

        Args:
            operation: The operation to retry
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            The result of the operation

        Raises:
            Exception: If the operation fails after all retries, includes job failure message if available
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    sleep(retry_delay)

        failure_message = self._get_job_failure_message()
        if failure_message:
            raise Exception(failure_message) from last_exception

        raise Exception(
            f"Operation failed after {max_retries} retries: {str(last_exception)}"
        ) from last_exception

    def _wait_for_status(
        self,
        target_statuses: list[str],
        check_interval: float = 5,
        status_message: str | None = None,
    ) -> str:
        """
        Wait until the job reaches one of the target statuses.

        Args:
            target_statuses: List of statuses to wait for
            check_interval: How often to check the status in seconds
            status_message: Optional message to display while waiting

        Returns:
            The final status reached
        """
        while (current_status := self.get_status()) not in target_statuses:
            if status_message:
                logger.debug(status_message, self, current_status)
            sleep(check_interval)

        return current_status

    @property
    def completed_at(self) -> datetime | None:
        """Returns the completion date of the job, or None if not completed."""
        if not self.__completed_at:
            self.__completed_at = self._openapi_service.order.job_api.job_job_id_get(
                self.id
            ).completed_at
        return self.__completed_at

    @property
    def pipeline_id(self) -> str:
        """Returns the pipeline ID of the job."""
        if not self.__pipeline_id:
            self.__pipeline_id = self._openapi_service.order.job_api.job_job_id_get(
                self.id
            ).pipeline_id
        return self.__pipeline_id

    @property
    def estimated_cost(self) -> CostEstimate:
        """An approximate cost estimate for running this job to completion.

        The estimate is not exact: the backend prices a sample of the rapids
        created so far (the job's first batch) and scales that per-response cost
        up to the total number of responses the job requires. The real cost can
        differ once every rapid has been priced.

        Right after a job is created the estimate is not yet available (the first
        batch of rapids is still being created and priced); this call polls until
        it becomes available.

        Raises:
            TimeoutError: If the estimate is still not available after a few minutes.
        """
        if self.__estimated_cost is None:
            with tracer.start_as_current_span("RapidataJob.estimated_cost"):
                model = _poll_for_cost_estimate(
                    lambda: self._openapi_service.order.job_api.job_job_id_cost_estimate_get(
                        self.id
                    ),
                    timeout=DEFAULT_ESTIMATE_TIMEOUT,
                    interval=DEFAULT_ESTIMATE_POLL_INTERVAL,
                )
                self.__estimated_cost = CostEstimate._from_model(model)
        return self.__estimated_cost

    @property
    def actual_cost(self) -> ActualCost | None:
        """The billed cost of this job, or None if it has not been billed yet.

        Derived from the customer's billing groups; returns None while no billing
        group exists for this job (e.g. the job has not produced billable
        responses yet). Unlike :attr:`estimated_cost`, this reflects the real
        amount charged.
        """
        with tracer.start_as_current_span("RapidataJob.actual_cost"):
            from rapidata.api_client.models.i_billing_group_model_audience_job_billing_group_model import (
                IBillingGroupModelAudienceJobBillingGroupModel,
            )

            page = 1
            page_size = 100
            while True:
                result = (
                    self._openapi_service.billing.billing_api.billing_costs_groups_get(
                        page=page,
                        page_size=page_size,
                    )
                )
                for group in result.items:
                    instance = group.actual_instance
                    if (
                        isinstance(
                            instance, IBillingGroupModelAudienceJobBillingGroupModel
                        )
                        and instance.job_id == self.id
                    ):
                        return ActualCost(
                            net_cost=instance.net_cost,
                            gross_cost=instance.gross_cost,
                            response_count=instance.response_count,
                        )

                if page * page_size >= result.total:
                    return None
                page += 1

    def get_status(self) -> str:
        """
        Gets the status of the job.

        Returns:
            The current status of the job as a string.
        """
        with tracer.start_as_current_span("RapidataJob.get_status"):
            return self._openapi_service.order.job_api.job_job_id_get(
                self.id
            ).state.value

    def _regenerate_results(self) -> None:
        """Triggers regeneration of a job whose results have gone stale.

        A ``StaleResults`` job no longer has a valid/available result file; retrying it
        re-runs the pipeline so a fresh result file is produced and the job completes
        again.
        """
        logger.info("Job '%s' has stale results, triggering regeneration", self)
        managed_print(
            f"Job '{self.name}' has stale results — regenerating, "
            "this may take a few minutes..."
        )
        self._openapi_service.order.job_api.job_job_id_retry_post(self.id)

    def get_results(self) -> RapidataResults:
        """
        Gets the results of the job.

        If the job is still processing, this method will block until the job is
        completed and then return the results.
        If the job's results have gone stale, regeneration is triggered automatically
        and this method blocks until the fresh results are ready.

        Returns:
            RapidataResults: The results of the job.

        Raises:
            Exception: If failed to get job results.
        """
        with tracer.start_as_current_span("RapidataJob.get_results"):
            from rapidata.api_client.exceptions import ApiException
            from rapidata.rapidata_client.results.rapidata_results import (
                RapidataResults,
            )

            logger.info("Getting results for job '%s'...", self)

            # Stale results have no downloadable file until the pipeline is re-run;
            # trigger that automatically before waiting for the re-completion.
            if self.get_status() == "StaleResults":
                self._regenerate_results()

            self._wait_for_status(
                target_statuses=["Completed", "Failed"],
                status_message="Job '%s' is in status %s, waiting for completion...",
            )

            try:
                results = (
                    self._openapi_service.order.job_api.job_job_id_download_results_get(
                        job_id=self.id
                    )
                )
                return RapidataResults(json.loads(results))
            except (ApiException, json.JSONDecodeError) as e:
                raise Exception(f"Failed to get job results: {str(e)}") from e

    def display_progress_bar(self, refresh_rate: int = 5) -> None:
        """
        Displays a progress bar for the job processing using tqdm.

        Args:
            refresh_rate: How often to refresh the progress bar, in seconds.

        Raises:
            ValueError: If refresh_rate is less than 1.
        """
        if refresh_rate < 1:
            raise ValueError("refresh_rate must be at least 1")

        current_status = self.get_status()
        if current_status == "Completed":
            managed_print(f"Job '{self}' is already completed.")
            return

        if current_status == "Failed":
            failure_message = self._get_job_failure_message()
            raise Exception(f"Job '{self}' has failed: {failure_message}")

        # Get progress from pipeline if available
        with tqdm(
            total=100,
            desc="Processing job",
            unit="%",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| completed [{elapsed}<{remaining}, {rate_fmt}]",
            disable=rapidata_config.logging.silent_mode,
        ) as pbar:
            last_percentage = 0
            while True:
                current_status = self.get_status()

                if current_status == "Completed":
                    pbar.update(100 - last_percentage)
                    break

                if current_status == "Failed":
                    failure_message = self._get_job_failure_message()
                    raise Exception(f"Job '{self}' has failed: {failure_message}")

                # Try to get progress from workflow
                try:
                    progress = self._get_workflow_progress()
                    current_percentage = (
                        progress.completion_percentage if progress else 0
                    )

                    if current_percentage > last_percentage:
                        pbar.update(current_percentage - last_percentage)
                        last_percentage = current_percentage
                except Exception:
                    pass  # Continue without progress update if we can't get it

                sleep(refresh_rate)

    def _get_workflow_progress(self):
        """Gets the workflow progress (internal use only)."""
        from rapidata.api_client.models.get_workflow_progress_result import (
            GetWorkflowProgressResult,
        )
        from rapidata.api_client.models.workflow_artifact_model import (
            WorkflowArtifactModel,
        )
        from rapidata.api_client.models.campaign_artifact_model import (
            CampaignArtifactModel,
        )
        from typing import cast

        try:
            with suppress_rapidata_error_logging():
                pipeline = self._openapi_service.pipeline.pipeline_api.pipeline_pipeline_id_get(
                    self.pipeline_id
                )
                workflow_id = cast(
                    WorkflowArtifactModel,
                    pipeline.artifacts["workflow-artifact"].actual_instance,
                ).workflow_id
                return self._openapi_service.workflow.workflow_api.workflow_workflow_id_progress_get(
                    workflow_id
                )
        except Exception:
            return None

    def delete(self) -> None:
        """Deletes the job."""
        with tracer.start_as_current_span("RapidataJob.delete"):
            logger.info("Deleting job '%s'", self)
            self._openapi_service.order.job_api.job_job_id_delete(self.id)
            logger.debug("Job '%s' has been deleted.", self)
            managed_print(f"Job '{self}' has been deleted.")

    def view(self) -> None:
        """Opens the job details page in the browser."""
        logger.info("Opening job details page in browser...")
        if not webbrowser.open(self.job_details_page):
            encoded_url = urllib.parse.quote(
                self.job_details_page, safe="%/:=&?~#+!$,;'@()*[]"
            )
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )

    def __str__(self) -> str:
        return f"RapidataJob(name='{self.name}', job_id='{self.id}')"

    def __repr__(self) -> str:
        return f"RapidataJob(name='{self.name}', job_id='{self.id}')"
