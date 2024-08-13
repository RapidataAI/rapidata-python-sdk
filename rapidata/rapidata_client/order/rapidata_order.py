from rapidata.rapidata_client.order.dataset.rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.workflow import Workflow
from rapidata.service import RapidataService


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
        self, name: str, workflow: Workflow, rapidata_service: RapidataService
    ):
        self.name = name
        self.workflow = workflow
        self.rapidata_service = rapidata_service
        self.order_id = None
        self._dataset = None

    def create(self):
        """
        Creates the order using the provided name and workflow.

        :return: The created RapidataOrder instance.
        :rtype: RapidataOrder
        """
        self.order_id, dataset_id = self.rapidata_service.order.create_order(self.name, self.workflow.to_dict())
        self._dataset = RapidataDataset(dataset_id, self.rapidata_service)
        return self

    def submit(self):
        """
        Submits the order for processing.

        :raises ValueError: If the order has not been created.
        """
        if self.order_id is None:
            raise ValueError("You must create the order before submitting it.")

        self.rapidata_service.order.submit(self.order_id)

    def approve(self):
        """
        Approves the order for execution.

        :raises ValueError: If the order has not been created.
        """
        if self.order_id is None:
            raise ValueError("You must create the order before approving it.")

        self.rapidata_service.order.approve(self.order_id)

    @property
    def dataset(self):
        """
        The dataset associated with the order.

        :raises ValueError: If the order has not been submitted.
        :return: The RapidataDataset instance.
        :rtype: RapidataDataset
        """
        if self._dataset is None:
            raise ValueError("You must submit the order before accessing the dataset.")
        return self._dataset
