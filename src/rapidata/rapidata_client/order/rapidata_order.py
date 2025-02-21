# Standard library imports
import json
import urllib.parse
import webbrowser
from time import sleep
from typing import Optional, cast, Any, Tuple
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

    Used to interact with a specific order in the Rapidata system. 
    Such as starting, pausing, and getting the results of the order.

    Args:
        name: The name of the order.
        order_id: The ID of the order.
        openapi_service: The OpenAPIService instance used to interact with the Rapidata API.
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

    def run(self, print_link: bool=True) -> "RapidataOrder":
        """
        Runs the order for to start collecting votes.
        """
        self.__openapi_service.order_api.order_submit_post(self.order_id)

        if print_link:
            print(f"Order '{self.name}' is now viewable under: https://app.{self.__openapi_service.enviroment}/order/detail/{self.order_id}")
        
        return self
    
    def pause(self) -> None:
        """
        Pauses the order.
        """
        self.__openapi_service.order_api.order_pause_post(self.order_id)
        print(f"Order '{self}' has been paused.")

    def unpause(self) -> None:
        """
        Unpauses/resume the order.
        """
        self.__openapi_service.order_api.order_resume_post(self.order_id)
        print(f"Order '{self}' has been unpaused.")

    def get_status(self) -> str:
        """
        Gets the status of the order.

        Different states are:
            Created: The order has been created but not started yet.\n
            Submitted: The order has been submitted and is being reviewed.\n
            ManualReview: The order is in manual review - something went wrong with the automatic approval.\n
            Processing: The order is actively being processed.\n
            Paused: The order has been paused.\n
            Completed: The order has been completed.\n
            Failed: The order has failed.
        
        Returns: 
            The status of the order.
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
            print(f"Order '{self.name}' is submitted and being reviewed. standby...", end="\r")
            sleep(1)

        if self.get_status() == OrderState.MANUALREVIEW:
            raise Exception(f"Order '{self.name}' is in manual review. It might take some time to start. To speed up the process, please contact support (info@rapidata.ai).\
                            \nOnce the order has started, you can run this method again to display the progress bar.")

        with tqdm(total=100, desc="Processing order", unit="%", bar_format="{desc}: {percentage:3.0f}%|{bar}| completed [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            last_percentage = 0
            while True:
                current_percentage = self.workflow_progress.completion_percentage
                if current_percentage > last_percentage:
                    pbar.update(current_percentage - last_percentage)
                    last_percentage = current_percentage

                if current_percentage >= 100:
                    break

                sleep(refresh_rate)

    @property
    def pipeline_id(self) -> str:
        """
        Gets the pipeline ID for the order.
        
        Returns:
            The pipeline ID.
        """
        if not self.__pipeline_id:
            self.__pipeline_id = self.__openapi_service.order_api.order_get_by_id_get(self.order_id).pipeline_id
        return self.__pipeline_id

    @property
    def workflow_id(self) -> str:
        """
        Gets the workflow ID for the order.
        
        Returns:
            The workflow ID.
        """
        if not self.__workflow_id:
            self._fetch_workflow_and_campaign_ids()
        return self.__workflow_id
    
    @property
    def campaign_id(self) -> str:
        """
        Gets the campaign ID for the order.
        
        Returns:
            The campaign ID.
        """
        if not self.__campaign_id:
            self._fetch_workflow_and_campaign_ids()
        return self.__campaign_id

    def _fetch_workflow_and_campaign_ids(self) -> None:
        """
        Fetches the workflow and campaign IDs from the pipeline.
        
        Raises:
            Exception: If the workflow ID cannot be retrieved.
        """
        if self.__workflow_id and self.__campaign_id:
            return

        for _ in range(10):  # Try for 20 seconds to get the workflow id
            try:
                pipeline = self.__openapi_service.pipeline_api.pipeline_id_get(self.pipeline_id)
                self.__workflow_id = cast(WorkflowArtifactModel, pipeline.artifacts["workflow-artifact"].actual_instance).workflow_id
                self.__campaign_id = cast(CampaignArtifactModel, pipeline.artifacts["campaign-artifact"].actual_instance).campaign_id
                return
            except Exception:
                sleep(2)

        raise Exception("Something went wrong when trying to get the order progress.")

    @property
    def workflow_progress(self):
        """
        Gets the workflow progress.
        
        Returns:
            The workflow progress.
            
        Raises:
            Exception: If the workflow progress cannot be retrieved.
        """
        progress = None
        for _ in range(2):
            try:
                progress = self.__openapi_service.workflow_api.workflow_get_progress_get(self.workflow_id)
                break
            except Exception:
                sleep(5)

        if not progress:
            raise Exception("Failed to get progress. Please try again in a few seconds.")
        
        return progress
    
    def __get_preliminary_results(self) -> RapidataResults:
        """
        Gets the preliminary results of the order.
        
        Returns:
            The preliminary results.
            
        Raises:
            Exception: If the preliminary results cannot be retrieved.
        """
        try: 
            download_id = self.__openapi_service.pipeline_api.pipeline_pipeline_id_preliminary_download_post(
                self.pipeline_id, 
                PreliminaryDownloadModel(sendEmail=False)
            ).download_id
            
            while not (preliminary_results := self.__openapi_service.pipeline_api.pipeline_preliminary_download_preliminary_download_id_get(
                preliminary_download_id=download_id
            )):
                sleep(1)
                
            return RapidataResults(json.loads(preliminary_results.decode()))
        
        except ApiException as e:
            # Handle API exceptions
            raise Exception(f"Failed to get preliminary order results: {str(e)}") from e
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            raise Exception(f"Failed to parse preliminary order results: {str(e)}") from e

    def get_results(self, preliminary_results: bool=False) -> RapidataResults:
        """
        Gets the results of the order. 
        If the order is still processing, this method will block until the order is completed and then return the results.

        Args:
            preliminary_results: If True, returns the preliminary results of the order. Defaults to False. 
                Note that preliminary results are not final and may not contain all the datapoints & responses. Only the onese that are already available.
                This will throw an exception if there are no responses available yet.

        Returns: 
            The results of the order.
        """

        if preliminary_results and self.get_status() not in [OrderState.COMPLETED]:
            return self.__get_preliminary_results()
        
        elif preliminary_results and self.get_status() in [OrderState.COMPLETED]:
            print("Order is already completed. Returning final results.")

        while self.get_status() not in [OrderState.COMPLETED, OrderState.PAUSED, OrderState.MANUALREVIEW, OrderState.FAILED]:
            sleep(5)

        try:
            # Get the raw result string
            return RapidataResults(self.__openapi_service.order_api.order_get_order_results_get(id=self.order_id)) # type: ignore
        
        except ApiException as e:
            # Handle API exceptions
            raise Exception(f"Failed to get order results: {str(e)}") from e
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            raise Exception(f"Failed to parse order results: {str(e)}") from e
        
    def preview(self) -> None:
        """
        Opens a preview of the campaign in the browser.
        """
        auth_url = f"https://rapids.{self.__openapi_service.enviroment}/preview/campaign?id={self.campaign_id}"
        could_open_browser = webbrowser.open(auth_url)

        if not could_open_browser:
            encoded_url = urllib.parse.quote(auth_url, safe="%/:=&?~#+!$,;'@()*[]")
            print(
                Fore.RED
                + f'Please open the following URL in your browser to log in: "{encoded_url}"'
                + Fore.RESET
            )
    
    def __str__(self) -> str:
        return f"name: '{self.name}' order id: {self.order_id}"
    
    def __repr__(self) -> str:
        return f"name: '{self.name}' order id: {self.order_id}"
