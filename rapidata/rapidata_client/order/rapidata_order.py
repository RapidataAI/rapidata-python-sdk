from openapi_client.models.create_order_model_referee import CreateOrderModelReferee
from openapi_client.models.create_order_model_workflow import CreateOrderModelWorkflow
from rapidata.rapidata_client.order.dataset.rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.workflow import Workflow
from openapi_client.api_client import ApiClient
from openapi_client.api.order_api import OrderApi
from openapi_client.models.create_order_model import CreateOrderModel
from rapidata.rapidata_client.referee import Referee
from rapidata.service.rapidata_api_services.rapidata_service import RapidataService


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

    def __init__(self, name: str, workflow: Workflow, referee: Referee, api_client: ApiClient, rapidata_service: RapidataService):
        self.name = name
        self.workflow = workflow
        self.referee = referee
        self.api_client = api_client
        self.rapidata_service = rapidata_service
        self.order_api = OrderApi(api_client)
        self.order_id = None
        self._dataset: RapidataDataset | None = None

    def create(self):
        """
        Creates the order using the provided name and workflow.

        :return: The created RapidataOrder instance.
        :rtype: RapidataOrder
        """
        order_model = CreateOrderModel(
            orderName=self.name,
            workflow=CreateOrderModelWorkflow(self.workflow.to_model()),
            userFilters=[],
            referee=CreateOrderModelReferee(self.referee.to_model())
        )

        result = self.order_api.order_create_post(create_order_model=order_model)
        self.order_id = result.order_id
        self._dataset = RapidataDataset(result.dataset_id, self.api_client, self.rapidata_service)
        return self

    def submit(self):
        """
        Submits the order for processing.

        :raises ValueError: If the order has not been created.
        """
        if self.order_id is None:
            raise ValueError("Order ID is None. Have you created the order?")

        self.order_api.order_submit_post(self.order_id)

    def approve(self):
        """
        Approves the order for execution.

        :raises ValueError: If the order has not been created.
        """
        if self.order_id is None:
            raise ValueError("You must create the order before approving it.")

        self.order_api.order_approve_post(self.order_id)

    @property
    def dataset(self):
        """
        The dataset associated with the order.

        :raises ValueError: If the order has not been submitted.
        :return: The RapidataDataset instance.
        :rtype: RapidataDataset
        """
        if self._dataset is None:
            raise ValueError("Datset is None. Have you created the order?")
        return self._dataset
