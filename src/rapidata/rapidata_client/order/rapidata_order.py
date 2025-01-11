from time import sleep
from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset
from rapidata.service.openapi_service import OpenAPIService
import json
from rapidata.api_client.exceptions import ApiException
from rapidata.api_client.models.order_state import OrderState
from typing import Optional, cast, Any
from rapidata.api_client.models.workflow_artifact_model import WorkflowArtifactModel
from tqdm import tqdm

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

    def __get_workflow_id(self):
        if self.__workflow_id:
            return self.__workflow_id

        for _ in range(10): # Try for 20 seconds to get the workflow id if workflow has not started by then, raise an exception
            try:
                order_result = self.__openapi_service.order_api.order_get_by_id_get(self.order_id)
                pipeline = self.__openapi_service.pipeline_api.pipeline_id_get(order_result.pipeline_id)
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

        
    def get_results(self) -> dict[str, Any]:
        """
        Gets the results of the order. 
        If the order is still processing, this method will block until the order is completed and then return the results.

        Returns: 
            The results of the order.
        """
        while self.get_status() not in [OrderState.COMPLETED, OrderState.PAUSED, OrderState.MANUALREVIEW, OrderState.FAILED]:
            sleep(5)

        try:
            # Get the raw result string
            return self.__openapi_service.order_api.order_get_order_results_get(id=self.order_id) # type: ignore
        
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
