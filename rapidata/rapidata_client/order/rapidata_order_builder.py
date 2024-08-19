from openapi_client.api_client import ApiClient
from rapidata.rapidata_client.referee.naive_referee import NaiveReferee
from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from openapi_client import ApiClient
from rapidata.rapidata_client.referee import Referee
from rapidata.service.rapidata_api_services.rapidata_service import RapidataService


class RapidataOrderBuilder:
    """
    Builder object for creating Rapidata orders.

    Use the fluent interface to set the desired configuration. Add a workflow to the order using `.workflow()` and finally call `.create()` to create the order.

    :param rapidata_service: The RapidataService instance.
    :type rapidata_service: RapidataService
    :param name: The name of the order.
    :type name: str
    """

    def __init__(
        self,
        api_client: ApiClient,
        rapidata_service: RapidataService,
        name: str,
    ):
        self._name = name
        self._api_client = api_client
        self._rapidata_service = rapidata_service
        self._workflow: Workflow | None = None
        self._referee: Referee | None = None

    def create(self) -> RapidataOrder:
        """
        Create a RapidataOrder instance based on the configured settings.

        :return: The created RapidataOrder instance.
        :rtype: RapidataOrder
        :raises ValueError: If no workflow is provided.
        """
        if self._workflow is None:
            raise ValueError("You must provide a blueprint to create an order.")
        
        if self._referee is None:
            print("No referee provided, using default NaiveReferee.")
            self._referee = NaiveReferee()

        order = RapidataOrder(
            name=self._name, workflow=self._workflow, referee=self._referee, api_client=self._api_client, rapidata_service=self._rapidata_service
        ).create()

        order.dataset.add_images_from_paths(self._image_paths)

        order.submit()

        return order


    def workflow(self, workflow: Workflow):
        """
        Set the workflow for the order.

        :param workflow: The workflow to be set.
        :type workflow: Workflow
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._workflow = workflow
        return self
    
    def referee(self, referee: Referee):
        """
        Set the referee for the order.

        :param referee: The referee to be set.
        :type referee: Referee
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._referee = referee
        return self
    
    def images(self, image_paths: list[str]):
        """
        Set the images for the order.

        :param image_paths: The image paths to be set.
        :type image_paths: list[str]
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._image_paths = image_paths
        return self
