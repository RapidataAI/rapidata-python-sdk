from rapidata.rapidata_client.dataset.rapidata_validation_set import (
    RapidataValidationSet,
)
from rapidata.rapidata_client.dataset.validation_set_builder import ValidationSetBuilder
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.utils.utils import Utils
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.dataset.rapidata_dataset import RapidataDataset



class RapidataClient:
    """The Rapidata client is the main entry point for interacting with the Rapidata API. It allows you to create orders and validation sets. For creating a new order, check out `new_order()`. For creating a new validation set, check out `new_validation_set()`."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str = "https://api.app.rapidata.ai",
    ):
        """Initialize the RapidataClient. Best practice is to store the client ID and client secret in environment variables. Ask your Rapidata representative for the client ID and client secret.

        Args:
            client_id (str): The client ID for authentication.
            client_secret (str): The client secret for authentication.
            endpoint (str, optional): The API endpoint URL.
        """
        self.openapi_service = OpenAPIService(
            client_id=client_id, client_secret=client_secret, endpoint=endpoint
        )

    def new_order(self, name: str) -> RapidataOrderBuilder:
        """Create a new order using a RapidataOrderBuilder instance.

        Args:
            name (str): The name of the order.

        Returns:
            RapidataOrderBuilder: A RapidataOrderBuilder instance.
        """
        return RapidataOrderBuilder(openapi_service=self.openapi_service, name=name)

    def new_validation_set(self, name: str) -> ValidationSetBuilder:
        """Create a new validation set using a ValidationDatasetBuilder instance.

        Args:
            name (str): The name of the validation set.

        Returns:
            ValidationSetBuilder: A ValidationDatasetBuilder instance.
        """
        return ValidationSetBuilder(name=name, openapi_service=self.openapi_service)

    def get_validation_set(self, validation_set_id: str) -> RapidataValidationSet:
        """Get a validation set by ID.

        Args:
            validation_set_id (str): The ID of the validation set.

        Returns:
            RapidataValidationSet: The ValidationSet instance.
        """
        return RapidataValidationSet(validation_set_id, self.openapi_service)
    
    def get_order(self, order_id: str) -> RapidataOrder:
        """Get an order by ID.

        Args:
            order_id (str): The ID of the order.

        Returns:
            RapidataOrder: The Order instance.
        """

        # TODO: check the pipeline for the dataset id - not really necessary atm
        # order = self.openapi_service.order_api.order_get_by_id_get(order_id)
        # pipeline = self.openapi_service..pipeline_get_by_id_get(order.pipeline_id)
        temp_dataset = RapidataDataset("temp", self.openapi_service)
        return RapidataOrder(
            dataset=temp_dataset, 
            order_id=order_id, 
            openapi_service=self.openapi_service)

    @property
    def utils(self) -> Utils:
        """Get the Utils instance.

        Returns:
            Utils: The Utils instance associated with this client.
        """
        return Utils(openapi_service=self.openapi_service)
