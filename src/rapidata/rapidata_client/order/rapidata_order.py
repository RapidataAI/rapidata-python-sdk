from time import sleep
from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset
from rapidata.service.openapi_service import OpenAPIService
import json
from rapidata.api_client.exceptions import ApiException
from rapidata.api_client.models.order_state import OrderState
from typing import Optional, cast, Any
from rapidata.api_client.models.workflow_artifact_model import WorkflowArtifactModel
from rapidata.api_client.models.preliminary_download_model import PreliminaryDownloadModel
from tqdm import tqdm
from rapidata.rapidata_client.order.rapidata_results import RapidataResults

class RapidataOrder:
    """
    An instance of a Rapidata order.

    Used to interact with a specific order in the Rapidata system. 
    Such as starting, pausing, and getting the results of the order.

    Args:
        name: The name of the order.
        order_id: The ID of the order.
        openapi_service: The OpenAPIService instance used to interact with the Rapidata API.
        dataset: The optional Dataset associated with the order.
    """

    def __init__(
        self,
        name: str,
        order_id: str,
        openapi_service: OpenAPIService,
        dataset: Optional[RapidataDataset]=None,
    ):
        self.order_id = order_id
        self.name = name
        self.__openapi_service = openapi_service
        self.__dataset = dataset
        self.__workflow_id = None
        self.__pipeline_id = ""

    def run(self, print_link: bool=True):
        """
        Runs the order for to start collecting votes.
        """
        self.__openapi_service.order_api.order_submit_post(self.order_id)

        if print_link:
            print(f"Order '{self.name}' is now viewable under: https://app.{self.__openapi_service.enviroment}/order/detail/{self.order_id}")
        
        return self
    
    def pause(self):
        """
        Pauses the order.
        """
        self.__openapi_service.order_api.order_pause_post(self.order_id)
        print(f"Order '{self}' has been paused.")

    def unpause(self):
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

    def display_progress_bar(self, refresh_rate: int=5):
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
                current_percentage = self.__get_workflow_progress().completion_percentage
                if current_percentage > last_percentage:
                    pbar.update(current_percentage - last_percentage)
                    last_percentage = current_percentage

                if current_percentage >= 100:
                    break

                sleep(refresh_rate)

    def __get_pipeline_id(self):
        if self.__pipeline_id:
            return self.__pipeline_id

        self.__pipeline_id = self.__openapi_service.order_api.order_get_by_id_get(self.order_id).pipeline_id
        return self.__pipeline_id

    def __get_workflow_id(self):
        if self.__workflow_id:
            return self.__workflow_id

        for _ in range(10): # Try for 20 seconds to get the workflow id if workflow has not started by then, raise an exception
            try:
                self.__get_pipeline_id()
                pipeline = self.__openapi_service.pipeline_api.pipeline_id_get(self.__pipeline_id)
                self.__workflow_id = cast(WorkflowArtifactModel, pipeline.artifacts["workflow-artifact"].actual_instance).workflow_id
                break
            except Exception:
                sleep(2)

        if not self.__workflow_id:
            raise Exception("Something went wrong when trying to get the order progress.")
        
        return self.__workflow_id
    
    def __get_workflow_progress(self):
        workflow_id = self.__get_workflow_id()
        progress = None
        for _ in range(2):
            try:
                progress = self.__openapi_service.workflow_api.workflow_get_progress_get(workflow_id)
                break
            except Exception:
                sleep(5)

        if not progress:
            raise Exception(f"Failed to get progress. Please try again in a few seconds.")
        
        return progress
    
    def __get_preliminary_results(self) -> RapidataResults:
        pipeline_id = self.__get_pipeline_id()
        try: 
            download_id = self.__openapi_service.pipeline_api.pipeline_pipeline_id_preliminary_download_post(pipeline_id, PreliminaryDownloadModel(sendEmail=False)).download_id
            while not (preliminary_results := self.__openapi_service.pipeline_api.pipeline_preliminary_download_preliminary_download_id_get(preliminary_download_id=download_id)):
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

    @property
    def dataset(self) -> RapidataDataset | None:
        """
        The dataset associated with the order.
        Returns: 
            The RapidataDataset instance.
        """
        return self.__dataset
    
    def __str__(self) -> str:
        return f"name: '{self.name}' order id: {self.order_id}"
    
    def __repr__(self) -> str:
        return f"name: '{self.name}' order id: {self.order_id}"
