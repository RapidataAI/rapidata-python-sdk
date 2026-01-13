from __future__ import annotations


# Standard library imports
import json
import urllib.parse
import webbrowser
from time import sleep
from typing import cast, Callable, TypeVar, TYPE_CHECKING
from colorama import Fore
from datetime import datetime
from tqdm import tqdm

# Local/application imports
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

if TYPE_CHECKING:
    from rapidata.api_client.models.campaign_artifact_model import CampaignArtifactModel
    from rapidata.api_client.models.file_stream_result import FileStreamResult
    from rapidata.api_client.models.order_state import OrderState
    from rapidata.api_client.models.workflow_artifact_model import WorkflowArtifactModel
    from rapidata.api_client.models.get_workflow_progress_result import (
        GetWorkflowProgressResult,
    )
    from rapidata.rapidata_client.results.rapidata_results import RapidataResults

T = TypeVar("T")


class RapidataOrder:
    """
    An instance of a Rapidata order.

    Used to interact with a specific order in the Rapidata system, such as starting,
    pausing, and retrieving results.

    Args:
        name: The name of the order.
        order_id: The ID of the order.
        openapi_service: The OpenAPIService instance for API interaction.
    """

    def __init__(
        self,
        name: str,
        order_id: str,
        openapi_service: OpenAPIService,
    ):
        self.id = order_id
        self.name = name
        self.__created_at: datetime | None = None
        self._openapi_service = openapi_service
        self.__workflow_id: str = ""
        self.__campaign_id: str = ""
        self.__pipeline_id: str = ""
        self.order_details_page = (
            f"https://app.{self._openapi_service.environment}/order/detail/{self.id}"
        )
        logger.debug("RapidataOrder initialized")

    def _get_order_failure_message(self) -> str | None:
        """Retrieves the failure message from the order if available."""
        try:
            order = self._openapi_service.order_api.order_order_id_get(self.id)
            return order.failure_message
        except Exception:
            logger.debug("Failed to get order failure message", self, exc_info=True)
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
            Exception: If the operation fails after all retries, includes order failure message if available
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    sleep(retry_delay)

        failure_message = self._get_order_failure_message()
        if failure_message:
            raise Exception(failure_message) from last_exception

        raise Exception(
            f"Operation failed after {max_retries} retries: {str(last_exception)}"
        ) from last_exception

    def _wait_for_state(
        self,
        target_states: list[OrderState],
        check_interval: float = 5,
        status_message: str | None = None,
    ) -> str:
        """
        Wait until the order reaches one of the target states.

        Args:
            target_states: List of states to wait for
            check_interval: How often to check the state in seconds
            status_message: Optional message to display while waiting

        Returns:
            The final state reached
        """
        while (current_state := self.get_status()) not in target_states:
            if status_message:
                logger.debug(status_message, self, current_state)
            sleep(check_interval)

        return current_state

    @property
    def created_at(self) -> datetime:
        """Returns the creation date of the order."""
        if not self.__created_at:
            self.__created_at = self._openapi_service.order_api.order_order_id_get(
                self.id
            ).order_date
        return self.__created_at

    def __get_pipeline_id(self) -> str:
        """Gets the pipeline ID for this order (cached, internal use only)."""
        if not self.__pipeline_id:
            self.__pipeline_id = self._retry_operation(
                lambda: self._openapi_service.order_api.order_order_id_get(
                    self.id
                ).pipeline_id,
            )
        return self.__pipeline_id

    def __get_workflow_id(self) -> str:
        """Gets the workflow ID for this order (cached, internal use only)."""
        if not self.__workflow_id:
            self.__load_workflow_and_campaign_ids()
        return self.__workflow_id

    def __get_campaign_id(self) -> str:
        """Gets the campaign ID for this order (cached, internal use only)."""
        if not self.__campaign_id:
            self.__load_workflow_and_campaign_ids()
        return self.__campaign_id

    def __load_workflow_and_campaign_ids(self) -> None:
        """Loads workflow and campaign IDs from the pipeline (with retry logic)."""
        if self.__workflow_id and self.__campaign_id:
            return

        def fetch_ids():
            from rapidata.api_client.models.workflow_artifact_model import (
                WorkflowArtifactModel,
            )
            from rapidata.api_client.models.campaign_artifact_model import (
                CampaignArtifactModel,
            )

            pipeline_id = self.__get_pipeline_id()
            pipeline = self._openapi_service.pipeline_api.pipeline_pipeline_id_get(
                pipeline_id
            )
            self.__workflow_id = cast(
                WorkflowArtifactModel,
                pipeline.artifacts["workflow-artifact"].actual_instance,
            ).workflow_id
            self.__campaign_id = cast(
                CampaignArtifactModel,
                pipeline.artifacts["campaign-artifact"].actual_instance,
            ).campaign_id

        self._retry_operation(fetch_ids)

    def __get_workflow_progress(self) -> GetWorkflowProgressResult:
        """Gets the workflow progress (internal use only)."""

        def get_progress():
            from rapidata.api_client.models.get_workflow_progress_result import (
                GetWorkflowProgressResult,
            )

            with suppress_rapidata_error_logging():
                workflow_id = self.__get_workflow_id()
                return self._openapi_service.workflow_api.workflow_workflow_id_progress_get(
                    workflow_id
                )

        return self._retry_operation(
            get_progress,
            max_retries=5,
            retry_delay=4,
        )

    def run(self) -> RapidataOrder:
        """Runs the order to start collecting responses."""
        with tracer.start_as_current_span("RapidataOrder.run"):
            from rapidata.api_client.models.submit_order_model import SubmitOrderModel

            logger.info("Starting order '%s'", self)
            self._openapi_service.order_api.order_order_id_submit_post(
                self.id, SubmitOrderModel(ignoreFailedDatapoints=True)
            )
            logger.debug("Order '%s' has been started.", self)
            managed_print(
                f"Order '{self.name}' is now viewable under: {self.order_details_page}"
            )
            return self

    def pause(self) -> None:
        """Pauses the order."""
        with tracer.start_as_current_span("RapidataOrder.pause"):
            logger.info("Pausing order '%s'", self)
            self._openapi_service.order_api.order_order_id_pause_post(self.id)
            logger.debug("Order '%s' has been paused.", self)
            managed_print(f"Order '{self}' has been paused.")

    def unpause(self) -> None:
        """Unpauses/resumes the order."""
        with tracer.start_as_current_span("RapidataOrder.unpause"):
            logger.info("Unpausing order '%s'", self)
            self._openapi_service.order_api.order_order_id_resume_post(self.id)
            logger.debug("Order '%s' has been unpaused.", self)
            managed_print(f"Order '{self}' has been unpaused.")

    def delete(self) -> None:
        """Deletes the order."""
        with tracer.start_as_current_span("RapidataOrder.delete"):
            logger.info("Deleting order '%s'", self)
            self._openapi_service.order_api.order_order_id_delete(self.id)
            logger.debug("Order '%s' has been deleted.", self)
            managed_print(f"Order '{self}' has been deleted.")

    def get_status(self) -> str:
        """
        Gets the status of the order.

        States:
            Created: The order has been created but not started yet.\n
            Preview: The order has been set up and ready but not collecting responses yet.\n
            Submitted: The order has been submitted and is being reviewed.\n
            ManualReview: The order is in manual review - something went wrong with the automatic approval.\n
            Processing: The order is actively being processed.\n
            Paused: The order has been paused.\n
            Completed: The order has been completed.\n
            Failed: The order has failed.
        """
        with tracer.start_as_current_span("RapidataOrder.get_status"):
            return self._openapi_service.order_api.order_order_id_get(self.id).state

    def display_progress_bar(self, refresh_rate: int = 5) -> None:
        """
        Displays a progress bar for the order processing using tqdm.

        Args:
            refresh_rate: How often to refresh the progress bar, in seconds.
        """
        from rapidata.api_client.models.order_state import OrderState

        if refresh_rate < 1:
            raise ValueError("refresh_rate must be at least 1")

        if self.get_status() == OrderState.CREATED:
            raise Exception("Order has not been started yet. Please start it first.")

        # Wait for submission review
        while self.get_status() == OrderState.SUBMITTED:
            managed_print(
                f"Order '{self}' is submitted and being reviewed. Standby...", end="\r"
            )
            sleep(1)

        if self.get_status() == OrderState.MANUALREVIEW:
            raise Exception(
                f"Order '{self}' is in manual review. It might take some time to start. "
                f"To speed up the process, contact support (info@rapidata.ai).\n"
                f"Once started, run this method again to display the progress bar."
            )

        with tqdm(
            total=100,
            desc="Processing order",
            unit="%",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| completed [{elapsed}<{remaining}, {rate_fmt}]",
            disable=rapidata_config.logging.silent_mode,
        ) as pbar:
            last_percentage = 0
            while True:
                current_percentage = (
                    self.__get_workflow_progress().completion_percentage
                )

                if current_percentage > last_percentage:
                    pbar.update(current_percentage - last_percentage)
                    last_percentage = current_percentage

                if current_percentage >= 100:
                    break

                sleep(refresh_rate)

    def get_results(self, preliminary_results: bool = False) -> RapidataResults:
        """
        Gets the results of the order.
        If the order is still processing, this method will block until the order is completed and then return the results.

        Args:
            preliminary_results: If True, returns the preliminary results of the order. Defaults to False.
                Note that preliminary results are not final and may not contain all the datapoints & responses. Only the ones that are already available.
        """
        with tracer.start_as_current_span("RapidataOrder.get_results"):
            from rapidata.api_client.models.order_state import OrderState
            from rapidata.api_client.exceptions import ApiException
            from rapidata.rapidata_client.results.rapidata_results import RapidataResults

            logger.info("Getting results for order '%s'...", self)

            if preliminary_results and self.get_status() not in [OrderState.COMPLETED]:
                return self._get_preliminary_results()

            if preliminary_results and self.get_status() == OrderState.COMPLETED:
                managed_print("Order is already completed. Returning final results.")

            self._wait_for_state(
                target_states=[
                    OrderState.COMPLETED,
                    OrderState.PAUSED,
                    OrderState.MANUALREVIEW,
                    OrderState.FAILED,
                ],
                status_message="Order '%s' is in state %s, waiting for completion...",
            )

            try:
                results = (
                    self._openapi_service.order_api.order_order_id_download_results_get(
                        order_id=self.id
                    )
                )
                return RapidataResults(json.loads(results))
            except (ApiException, json.JSONDecodeError) as e:
                raise Exception(f"Failed to get order results: {str(e)}") from e

    def _get_preliminary_results(self) -> RapidataResults:
        """Fetches preliminary results for an in-progress order."""
        from rapidata.api_client.models.preliminary_download_model import (
            PreliminaryDownloadModel,
        )
        from rapidata.api_client.exceptions import ApiException
        from rapidata.rapidata_client.results.rapidata_results import RapidataResults

        try:
            pipeline_id = self.__get_pipeline_id()
            download_id = self._openapi_service.pipeline_api.pipeline_pipeline_id_preliminary_download_post(
                pipeline_id, PreliminaryDownloadModel(sendEmail=False)
            ).download_id

            def check_results():
                results = self._openapi_service.pipeline_api.pipeline_preliminary_download_preliminary_download_id_get(
                    preliminary_download_id=download_id
                )
                return RapidataResults(json.loads(results))

            return self._retry_operation(
                check_results,
                max_retries=60,
                retry_delay=1,
            )

        except (ApiException, json.JSONDecodeError) as e:
            raise Exception(f"Failed to get preliminary results: {str(e)}") from e

    def view(self) -> None:
        """Opens the order details page in the browser."""
        logger.info("Opening order details page in browser...")
        if not webbrowser.open(self.order_details_page):
            encoded_url = urllib.parse.quote(
                self.order_details_page, safe="%/:=&?~#+!$,;'@()*[]"
            )
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )

    def preview(self) -> None:
        """Opens a preview of the order in the browser."""
        from rapidata.api_client.models.order_state import OrderState
        from rapidata.api_client.models.preview_order_model import PreviewOrderModel

        logger.info("Opening order preview in browser...")

        if self.get_status() == OrderState.CREATED:
            logger.info("Order is still in state created. Setting it to preview.")
            self._openapi_service.order_api.order_order_id_preview_post(
                self.id, PreviewOrderModel(ignoreFailedDatapoints=True)
            )
            logger.info("Order is now in preview state.")

        campaign_id = self.__get_campaign_id()
        auth_url = f"https://app.{self._openapi_service.environment}/order/detail/{self.id}/preview?campaignId={campaign_id}"

        if not webbrowser.open(auth_url):
            encoded_url = urllib.parse.quote(auth_url, safe="%/:=&?~#+!$,;'@()*[]")
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )

    def __str__(self) -> str:
        return f"RapidataOrder(name='{self.name}', order_id='{self.id}')"

    def __repr__(self) -> str:
        return f"RapidataOrder(name='{self.name}', order_id='{self.id}')"
