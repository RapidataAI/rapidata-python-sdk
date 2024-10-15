import time
from rapidata.rapidata_client.dataset.rapidata_dataset import RapidataDataset
from rapidata.service.openapi_service import OpenAPIService
import json
from rapidata.api_client.exceptions import ApiException
from typing import cast
from rapidata.api_client.models.workflow_artifact_model import WorkflowArtifactModel
from tqdm import tqdm

class RapidataOrder:
    """
    Represents a Rapidata order.

    :param name: The name of the order.
    :type name: str
    :param workflow: The workflow associated with the order.
    :type workflow: Workflow
    :param rapidata_service: The Rapidata service used to create and manage the order.
    :type rapidata_service: RapidataService
    """

    def __init__(
        self,
        order_id: str,
        dataset: RapidataDataset,
        openapi_service: OpenAPIService,
    ):
        self.openapi_service = openapi_service
        self.order_id = order_id
        self._dataset = dataset
        self._workflow_id = None

    def submit(self):
        """
        Submits the order for processing.
        """

        self.openapi_service.order_api.order_submit_post(self.order_id)

    def approve(self):
        """
        Approves the order for execution.
        """
        self.openapi_service.order_api.order_approve_post(self.order_id)

    def get_status(self):
        """
        Gets the status of the order.

        :return: The status of the order.
        :rtype: str
        """
        return self.openapi_service.order_api.order_get_by_id_get(self.order_id)

    def display_progress_bar(self, refresh_rate=5):
        """
        Displays a progress bar for the order processing using tqdm.
        
        :param refresh_rate: How often to refresh the progress bar, in seconds.
        :type refresh_rate: float
        """
        total_rapids = self._get_total_rapids()
        with tqdm(total=total_rapids, desc="Processing order", unit="rapids") as pbar:
            completed_rapids = 0
            while True:
                current_completed = self._get_completed_rapids()
                if current_completed > completed_rapids:
                    pbar.update(current_completed - completed_rapids)
                    completed_rapids = current_completed
                
                if completed_rapids >= total_rapids:
                    break
                
                time.sleep(refresh_rate)

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
                time.sleep(2)
        if not self._workflow_id:
            raise Exception("Order has not started yet. Please wait for a few seconds and try again.")
        return self._workflow_id
    
    def _get_total_rapids(self):
        workflow_id = self._get_workflow_id()
        return self.openapi_service.workflow_api.workflow_get_progress_get(workflow_id).total

    def _get_completed_rapids(self):
        workflow_id = self._get_workflow_id()
        return self.openapi_service.workflow_api.workflow_get_progress_get(workflow_id).completed

    def get_progress_percentage(self):
        workflow_id = self._get_workflow_id()
        progress = self.openapi_service.workflow_api.workflow_get_progress_get(workflow_id)
        return progress.completion_percentage

    def get_results(self):
        """
        Gets the results of the order.

        :return: The results of the order.
        :rtype: dict
        """
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
    def dataset(self):
        """
        The dataset associated with the order.
        :return: The RapidataDataset instance.
        :rtype: RapidataDataset
        """
        return self._dataset
