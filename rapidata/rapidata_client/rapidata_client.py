from rapidata.rapidata_client.order.dataset.validation_set_builder import ValidationSetBuilder
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.service.openapi_service import OpenAPIService

class RapidataClient:
    """
    A client for interacting with the Rapidata API.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str = "https://api.app.rapidata.ai",
    ):
        """
        Initialize the RapidataClient.

        :param client_id: The client ID for authentication.
        :param client_secret: The client secret for authentication.
        :param endpoint: The API endpoint URL. Defaults to "https://api.rapidata.ai".
        """
        self.openapi_service = OpenAPIService(
            client_id=client_id, client_secret=client_secret, endpoint=endpoint
        )

        

    def new_order(self, name: str) -> RapidataOrderBuilder:
        """
        Create a new order using a RapidataOrderBuilder instance.

        :param name: The name of the order.
        :return: A RapidataOrderBuilder instance.
        """
        return RapidataOrderBuilder(openapi_service=self.openapi_service, name=name)
    

    def new_validation_set(self, name: str) -> ValidationSetBuilder:
        """
        Create a new validation set using a ValidationDatasetBuilder instance.

        :param name: The name of the validation set.
        :return: A ValidationDatasetBuilder instance.
        """
        return ValidationSetBuilder(name=name, openapi_service=self.openapi_service)
