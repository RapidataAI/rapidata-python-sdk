import time
from rapidata.rapidata_client.dataset.rapidata_dataset import RapidataDataset
from rapidata.service.openapi_service import OpenAPIService


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

    def wait_for_done(self):
        """
        Blocking call that waits for the order to be done. Exponential backoff is used to check the status of the order.
        """
        wait_time = 2
        back_off_factor = 1.5
        minimum_poll_interval = 60 * 10  # 10 minutes

        while True:
            time.sleep(wait_time)
            result = self.get_status()
            if result.state == "Completed":
                break
            wait_time = max(
                minimum_poll_interval, wait_time * back_off_factor
            )  # poll at least every 10 minutes

    def get_results(self):
        """
        Gets the results of the order.

        :return: The results of the order.
        :rtype: dict
        """
        # return self.openapi_service.order_api.order_get_order_results_get(self.order_id) # throws error
        raise NotImplementedError("Currently not supported")

    @property
    def dataset(self):
        """
        The dataset associated with the order.
        :return: The RapidataDataset instance.
        :rtype: RapidataDataset
        """
        return self._dataset
