from openapi_client.api_client import ApiClient
from openapi_client.configuration import Configuration
from openapi_client.api.identity_api import IdentityApi
from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.service.rapidata_api_services.rapidata_service import RapidataService

class RapidataClient:
    """
    A client for interacting with the Rapidata API.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str = "https://api.rapidata.ai",
    ):
        """
        Initialize the RapidataClient.

        :param client_id: The client ID for authentication.
        :param client_secret: The client secret for authentication.
        :param endpoint: The API endpoint URL. Defaults to "https://api.rapidata.ai".
        """

        client_configuration = Configuration(host=endpoint)
        self.api_client = ApiClient(configuration=client_configuration)
        self.rapidata_service = RapidataService(client_id=client_id, client_secret=client_secret, endpoint=endpoint)

        identity_api = IdentityApi(self.api_client)

        result = identity_api.identity_get_client_auth_token_post(
            client_id=client_id,
            _headers={"Authorization": f"Basic {client_secret}"},
        )

        client_configuration.api_key["bearer"] = f"Bearer {result.auth_token}"

    def new_order(self, name: str) -> RapidataOrderBuilder:
        """
        Create a new order using a RapidataOrderBuilder instance.

        :param name: The name of the order.
        :return: A RapidataOrderBuilder instance.
        """
        return RapidataOrderBuilder(api_client=self.api_client, name=name, rapidata_service=self.rapidata_service)
