from rapidata.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from rapidata.service import RapidataService


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
        self._rapidata_service = RapidataService(
            client_id=client_id, client_secret=client_secret, endpoint=endpoint
        )

    def new_order(self, name: str) -> RapidataOrderBuilder:
        """
        Create a new order using a RapidataOrderBuilder instance.

        :param name: The name of the order.
        :return: A RapidataOrderBuilder instance.
        """
        return RapidataOrderBuilder(rapidata_service=self._rapidata_service, name=name)
