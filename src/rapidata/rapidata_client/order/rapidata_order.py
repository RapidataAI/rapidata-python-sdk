# Standard library imports
import json
import urllib.parse
import webbrowser
from time import sleep
from typing import cast
from colorama import Fore

# Third-party imports
from tqdm import tqdm

# Local/application imports
from rapidata.api_client.exceptions import ApiException
from rapidata.api_client.models.campaign_artifact_model import CampaignArtifactModel
from rapidata.api_client.models.order_state import OrderState
from rapidata.api_client.models.preliminary_download_model import PreliminaryDownloadModel
from rapidata.api_client.models.workflow_artifact_model import WorkflowArtifactModel
from rapidata.rapidata_client.order.rapidata_results import RapidataResults
from rapidata.service.openapi_service import OpenAPIService


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
        self.order_id = order_id
        self.name = name
        self.__openapi_service = openapi_service
        self.__workflow_id: str = ""
        self.__campaign_id: str = ""
        self.__pipeline_id: str = ""
        self._max_retries = 10  
        self._retry_delay = 2   

    def run(self, print_link: bool = True) -> "RapidataOrder":
        """Runs the order to start collecting responses."""
        self.__openapi_service.order_api.order_submit_post(self.order_id)
        if print_link:
            print(f"Order '{self.name}' is now viewable under: https://app.{self.__openapi_service.enviroment}/order/detail/{self.order_id}")
        return self

    def pause(self) -> None:
        """Pauses the order."""
        self.__openapi_service.order_api.order_pause_post(self.order_id)
        print(f"Order '{self}' has been paused.")

    def unpause(self) -> None:
        """Unpauses/resumes the order."""
        self.__openapi_service.order_api.order_resume_post(self.order_id)
        print(f"Order '{self}' has been unpaused.")

    def get_status(self) -> str:
        """
        Gets the status of the order.

        States:
            Created: The order has been created but not started yet.\n
            Submitted: The order has been submitted and is being reviewed.\n
            ManualReview: The order is in manual review - something went wrong with the automatic approval.\n
            Processing: The order is actively being processed.\n
            Paused: The order has been paused.\n
            Completed: The order has been completed.\n
            Failed: The order has failed.
        """
        return self.__openapi_service.order_api.order_get_by_id_get(self.order_id).state

    def display_progress_bar(self, refresh_rate: int=5) -> None:
        """
        Displays a progress bar for the order processing using tqdm.
        
        Args: 
            refresh_rate: How often to refresh the progress bar, in seconds.
        """
        if refresh_rate < 1:
            raise ValueError("refresh_rate must be at least 1")
        
        if self.get_status() == OrderState.CREATED:
            raise Exception("Order has not been started yet. Please start it first.")
        
        while self.get_status() == OrderState.SUBMITTED:
            print(f"Order '{self.name}' is submitted and being reviewed. Standby...", end="\r")
            sleep(1)

        if self.get_status() == OrderState.MANUALREVIEW:
            raise Exception(
                f"Order '{self.name}' is in manual review. It might take some time to start. "
                "To speed up the process, contact support (info@rapidata.ai).\n"
                "Once started, run this method again to display the progress bar."
            )

        with tqdm(total=100, desc="Processing order", unit="%", bar_format="{desc}: {percentage:3.0f}%|{bar}| completed [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            last_percentage = 0
            while True:
                current_percentage = self._workflow_progress.completion_percentage
                if current_percentage > last_percentage:
                    pbar.update(current_percentage - last_percentage)
                    last_percentage = current_percentage

                if current_percentage >= 100:
                    break

                sleep(refresh_rate)

    @property
    def _workflow_progress(self):
        """
        Gets the workflow progress.
        """
        progress = None
        for _ in range(self._max_retries // 2):
            try:
                workflow_id = self.__get_workflow_id()
                progress = self.__openapi_service.workflow_api.workflow_get_progress_get(workflow_id)
                break
            except Exception:
                sleep(self._retry_delay * 2)
        if not progress:
            raise Exception("Failed to get progress. Please try again later.")
        return progress

    def get_results(self, preliminary_results: bool = False) -> RapidataResults:
        """
        Gets the results of the order. 
        If the order is still processing, this method will block until the order is completed and then return the results.

        Args:
            preliminary_results: If True, returns the preliminary results of the order. Defaults to False. 
                Note that preliminary results are not final and may not contain all the datapoints & responses. Only the onese that are already available.
                This will throw an exception if there are no responses available yet.
        """

        if preliminary_results and self.get_status() not in [OrderState.COMPLETED]:
            return self.__get_preliminary_results()
        
        elif preliminary_results and self.get_status() in [OrderState.COMPLETED]:
            print("Order is already completed. Returning final results.")

        while self.get_status() not in [OrderState.COMPLETED, OrderState.PAUSED, OrderState.MANUALREVIEW, OrderState.FAILED]:
            sleep(5)

        try:
            return RapidataResults(self.__openapi_service.order_api.order_get_order_results_get(id=self.order_id)) # type: ignore
        except (ApiException, json.JSONDecodeError) as e:
            raise Exception(f"Failed to get order results: {str(e)}") from e
        
    def preview(self) -> None:
        """
        Opens a preview of the order in the browser.
        
        Raises:
            Exception: If the order is not in processing state.
        """
        if self.get_status() != OrderState.PROCESSING:
            raise Exception("Order is not processing. Preview unavailable.")
        
        campaign_id = self.__get_campaign_id()
        auth_url = f"https://rapids.{self.__openapi_service.enviroment}/preview/campaign?id={campaign_id}"
        could_open_browser = webbrowser.open(auth_url)
        if not could_open_browser:
            encoded_url = urllib.parse.quote(auth_url, safe="%/:=&?~#+!$,;'@()*[]")
            print(Fore.RED + f'Please open this URL in your browser: "{encoded_url}"' + Fore.RESET)

    def __get_pipeline_id(self) -> str:
        """Internal method to fetch and cache the pipeline ID."""
        if not self.__pipeline_id:
            for _ in range(self._max_retries):
                try:
                    self.__pipeline_id = self.__openapi_service.order_api.order_get_by_id_get(self.order_id).pipeline_id
                    break
                except Exception:
                    sleep(self._retry_delay)
            else:
                raise Exception("Failed to fetch pipeline ID after retries.")
        return self.__pipeline_id

    def __get_workflow_id(self) -> str:
        """Internal method to fetch and cache the workflow ID."""
        if not self.__workflow_id:
            self.__fetch_workflow_and_campaign_ids()
        return self.__workflow_id

    def __get_campaign_id(self) -> str:
        """Internal method to fetch and cache the campaign ID."""
        if not self.__campaign_id:
            self.__fetch_workflow_and_campaign_ids()
        return self.__campaign_id

    def __fetch_workflow_and_campaign_ids(self) -> None:
        """Fetches workflow and campaign IDs from the pipeline."""
        if self.__workflow_id and self.__campaign_id:
            return
        pipeline_id = self.__get_pipeline_id()
        for _ in range(self._max_retries):
            try:
                pipeline = self.__openapi_service.pipeline_api.pipeline_id_get(pipeline_id)
                self.__workflow_id = cast(WorkflowArtifactModel, pipeline.artifacts["workflow-artifact"].actual_instance).workflow_id
                self.__campaign_id = cast(CampaignArtifactModel, pipeline.artifacts["campaign-artifact"].actual_instance).campaign_id
                return
            except Exception:
                sleep(self._retry_delay)
        raise Exception("Failed to fetch workflow and campaign IDs after retries.")

    def __get_preliminary_results(self) -> RapidataResults:
        """Internal method to fetch preliminary results."""
        try:
            pipeline_id = self.__get_pipeline_id()
            download_id = self.__openapi_service.pipeline_api.pipeline_pipeline_id_preliminary_download_post(
                pipeline_id, PreliminaryDownloadModel(sendEmail=False)
            ).download_id
            
            elapsed = 0
            timeout = 60
            while elapsed < timeout:
                preliminary_results = self.__openapi_service.pipeline_api.pipeline_preliminary_download_preliminary_download_id_get(
                    preliminary_download_id=download_id
                )
                if preliminary_results:
                    return RapidataResults(json.loads(preliminary_results.decode()))
                sleep(1)
                elapsed += 1
            raise Exception("Timeout waiting for preliminary results.")
        except (ApiException, json.JSONDecodeError) as e:
            raise Exception(f"Failed to get preliminary results: {str(e)}") from e

    def __str__(self) -> str:
        return f"name: '{self.name}' order id: {self.order_id}"

    def __repr__(self) -> str:
        return f"RapidataOrder(name='{self.name}', order_id='{self.order_id}')"
