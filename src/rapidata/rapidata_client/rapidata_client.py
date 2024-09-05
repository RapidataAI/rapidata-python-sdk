from rapidata.rapidata_client.dataset.rapidata_validation_set import (
    RapidataValidationSet,
)
from rapidata.rapidata_client.dataset.validation_set_builder import ValidationSetBuilder
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.utils.utils import Utils
from rapidata.service.openapi_service import OpenAPIService


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

    @property
    def utils(self) -> Utils:
        """Get the Utils instance.

        Returns:
            Utils: The Utils instance associated with this client.
        """
        return Utils(openapi_service=self.openapi_service)
