from time import sleep
from rapidata.rapidata_client.dataset.rapidata_dataset import RapidataDataset
from rapidata.service.openapi_service import OpenAPIService
import json
from rapidata.api_client.exceptions import ApiException
from typing import Optional, cast, Any
from rapidata.api_client.models.workflow_artifact_model import WorkflowArtifactModel
from tqdm import tqdm

class RapidataOrder:
    """
    Represents a Rapidata order.

    Args:
        The ID of the order.
        The optional Dataset associated with the order.
        The OpenAPIService instance used to interact with the Rapidata API.
        The name of the order.
    """

    def __init__(
        self,
        order_id: str,
        dataset: Optional[RapidataDataset],
        openapi_service: OpenAPIService,
        name: str,
    ):
        self.openapi_service = openapi_service
        self.order_id = order_id
        self._dataset = dataset
        self.name = name
        self._workflow_id = None

    def submit(self):
        """
        Submits the order for processing.
        """
        self.openapi_service.order_api.order_submit_post(self.order_id)

    def get_status(self) -> str:
        """
        Gets the status of the order.
        
        Returns: 
            The status of the order.
        """
        return self.openapi_service.order_api.order_get_by_id_get(self.order_id).state

    def display_progress_bar(self, refresh_rate=5):
        """
        Displays a progress bar for the order processing using tqdm.
        
        Prameter: 
            How often to refresh the progress bar, in seconds.
        """
        total_rapids = self._get_workflow_progress().total
        with tqdm(total=total_rapids, desc="Processing order", unit="rapids") as pbar:
            completed_rapids = 0
            while True:
                current_completed = self._get_workflow_progress().completed
                if current_completed > completed_rapids:
                    pbar.update(current_completed - completed_rapids)
                    completed_rapids = current_completed

                if completed_rapids >= total_rapids:
                    break

                sleep(refresh_rate)

    def _get_workflow_id(self):
        if self._workflow_id:
            return self._workflow_id

        for _ in range(2):
            try:
                order_result = self.openapi_service.order_api.order_get_by_id_get(self.order_id)
                pipeline = self.openapi_service.pipeline_api.pipeline_id_get(order_result.pipeline_id)
                self._workflow_id = cast(WorkflowArtifactModel, pipeline.artifacts["workflow-artifact"].actual_instance).workflow_id
                break
            except Exception:
                sleep(2)
        if not self._workflow_id:
            raise Exception("Order has not started yet. Please start it or wait for a few seconds and try again.")
        return self._workflow_id
    
    def _get_workflow_progress(self):
        workflow_id = self._get_workflow_id()
        progress = None
        for _ in range(2):
            try:
                progress = self.openapi_service.workflow_api.workflow_get_progress_get(workflow_id)
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
        while self.get_status() == "Processing":
            sleep(5)

        try:
            # Get the raw result string
            result_str = self.openapi_service.order_api.order_result_get(id=self.order_id)
            # Parse the result string as JSON
            return json.loads(result_str)
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
        return self._dataset
