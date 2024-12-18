from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.order.rapidata_order_manager import RapidataOrderManager

from rapidata.rapidata_client.validation.validation_set_manager import ValidationSetManager


class RapidataClient:
    """The Rapidata client is the main entry point for interacting with the Rapidata API. It allows you to create orders and validation sets."""
    
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        enviroment: str = "rapidata.ai",
        oauth_scope: str = "openid",
        cert_path: str | None = None,
    ):
        """Initialize the RapidataClient. If both the client_id and client_secret are None, it will try using your credentials under "~/.config/rapidata/credentials.json". 
        If this is not successful, it will open a browser windown and ask you to log in, then save your new credentials in said json file.

        Args:
            client_id (str): The client ID for authentication.
            client_secret (str): The client secret for authentication.
            enviroment (str, optional): The API endpoint.

        Attributes:
            order (RapidataOrderManager): The RapidataOrderManager instance.
            validation (ValidationSetManager): The ValidationSetManager instance.
        """
        self._openapi_service = OpenAPIService(
            client_id=client_id,
            client_secret=client_secret,
            enviroment=enviroment,
            oauth_scope=oauth_scope,
            cert_path=cert_path
        )
        
        self.order = RapidataOrderManager(openapi_service=self._openapi_service)
        
        self.validation = ValidationSetManager(openapi_service=self._openapi_service)
