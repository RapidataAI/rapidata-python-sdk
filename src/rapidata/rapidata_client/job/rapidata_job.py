from __future__ import annotations

import json
import urllib.parse
import webbrowser
from datetime import datetime
from time import sleep
from typing import Callable, TypeVar, TYPE_CHECKING
from colorama import Fore
from tqdm.auto import tqdm

from rapidata.api_client.models.audience_job_state import AudienceJobState
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
    CostEstimate,
    DEFAULT_ESTIMATE_POLL_INTERVAL,
    DEFAULT_ESTIMATE_TIMEOUT,
    _poll_for_cost_estimate,
)

if TYPE_CHECKING:
    from rapidata.api_client.models.get_job_by_id_endpoint_output import (
        GetJobByIdEndpointOutput,
    )
    from rapidata.rapidata_client.results.rapidata_results import RapidataResults
    from rapidata.rapidata_client.job.progress import JobProgress
    from rapidata.rapidata_client.audience.recruiting import RecruitingMetrics

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

    # States a job can settle into that will never progress to Completed/Failed on
    # their own: ManualApproval needs a Rapidata reviewer to act, SpendLimited needs
    # an account top-up. Waiting on either (e.g. from get_results) would hang the
    # caller forever, so we surface them as informative errors instead.
    _BLOCKING_STATUSES = (
        AudienceJobState.MANUALAPPROVAL,
        AudienceJobState.SPENDLIMITED,
    )

    def _fetch_job(self) -> GetJobByIdEndpointOutput:
        """Fetches the job's GET output (state, failure message, review reason)."""
        return self._openapi_service.order.job_api.job_job_id_get(self.id)

    def _get_job_failure_message(self) -> str | None:
        """Retrieves the failure message from the job if available."""
        try:
            return self._fetch_job().failure_message
        except Exception:
            logger.debug("Failed to get job failure message", self, exc_info=True)
            return None

    def _raise_for_blocking_status(self, job: GetJobByIdEndpointOutput) -> None:
        """Raises an informative error for a job state that can't reach completion
        on its own, instead of letting the caller block on it indefinitely."""
        if job.state == AudienceJobState.SPENDLIMITED:
            raise Exception(
                f"Job '{self}' is spend-limited: the account ran out of funds while "
                f"running, so it stopped collecting responses. Partial results remain "
                f"available; top up the account to resume and let the job finish."
            )

        # ManualApproval — reviewReason is optional; a job can legitimately be under
        # review with no customer-facing reason recorded yet.
        reason = job.review_reason
        reason_detail = f" ({reason.value})" if reason else ""
        raise Exception(
            f"Job '{self}' is being reviewed{reason_detail}: a Rapidata reviewer "
            f"needs to approve it before it runs. This can take a couple of hours; "
            f"once approved, call this again."
        )

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

        Raises:
            Exception: If the job enters a state it can't progress out of on its own
                (``ManualApproval`` or ``SpendLimited``) while a different status is
                being awaited — with the review reason when the API provides one.
        """
        while True:
            job = self._fetch_job()
            current_status = job.state.value
            if current_status in target_statuses:
                return current_status
            if current_status in self._BLOCKING_STATUSES:
                self._raise_for_blocking_status(job)
            if status_message:
                logger.debug(status_message, self, current_status)
            sleep(check_interval)

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
        """An approximate estimate of what this job will cost to run to completion.

        This is an estimate, not the final bill - see :class:`CostEstimate`. The
        estimate is priced shortly after the job is created; this call waits for
        it to become available.

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

    def get_status(self) -> str:
        """
        Gets the status of the job.

        Returns:
            The current status of the job as a string.
        """
        with tracer.start_as_current_span("RapidataJob.get_status"):
            return self._fetch_job().state.value

    def get_progress(self) -> JobProgress:
        """Gets a snapshot of how far along the job is.

        Unlike :py:meth:`get_status`, which only reports the coarse job state, this
        returns the labeling completion percentage and — for custom audiences — the
        recruiting funnel of the annotator pool behind the job, so you can tell normal
        labeling from a job that is waiting on recruiting or has stalled.

        This does not block: it reports the current progress and returns immediately.

        Returns:
            JobProgress: The current progress of the job.
        """
        with tracer.start_as_current_span("RapidataJob.get_progress"):
            from rapidata.rapidata_client.job.progress import JobProgress

            job = self._fetch_job()
            workflow_progress = self._get_workflow_progress()

            return JobProgress(
                state=job.state.value,
                completion_percentage=(
                    float(workflow_progress.completion_percentage)
                    if workflow_progress
                    else 0.0
                ),
                recruiting=self._get_recruiting_metrics(),
            )

    def _get_recruiting_metrics(self) -> RecruitingMetrics | None:
        """Gets the recruiting funnel for the job's audience, or ``None`` for curated
        audiences (which report no per-state users because they do not recruit)."""
        from rapidata.rapidata_client.audience.recruiting import RecruitingMetrics

        try:
            with suppress_rapidata_error_logging():
                metrics = self._openapi_service.audience.audience_api.audience_audience_id_user_metrics_get(
                    self.audience_id
                )
        except Exception:
            logger.debug(
                "Failed to get recruiting metrics for job '%s'", self, exc_info=True
            )
            return None

        users_per_state = metrics.users_per_state or {}
        if not users_per_state:
            return None

        return RecruitingMetrics._from_users_per_state(users_per_state)

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
            Exception: If failed to get job results, or if the job is in manual
                review (``ManualApproval``) or spend-limited (``SpendLimited``) and
                therefore cannot complete without intervention.
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
            Exception: If the job has failed, or is in a state it can't progress out
                of on its own (``ManualApproval`` or ``SpendLimited``).
        """
        if refresh_rate < 1:
            raise ValueError("refresh_rate must be at least 1")

        job = self._fetch_job()
        if job.state == AudienceJobState.COMPLETED:
            managed_print(f"Job '{self}' is already completed.")
            return

        if job.state == AudienceJobState.FAILED:
            raise Exception(f"Job '{self}' has failed: {job.failure_message}")

        if job.state in self._BLOCKING_STATUSES:
            self._raise_for_blocking_status(job)

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
                job = self._fetch_job()

                if job.state == AudienceJobState.COMPLETED:
                    pbar.update(100 - last_percentage)
                    break

                if job.state == AudienceJobState.FAILED:
                    raise Exception(f"Job '{self}' has failed: {job.failure_message}")

                if job.state in self._BLOCKING_STATUSES:
                    self._raise_for_blocking_status(job)

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
