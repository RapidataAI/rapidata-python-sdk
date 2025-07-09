import requests
from packaging import version
from rapidata import __version__

from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.order.rapidata_order_manager import RapidataOrderManager
from rapidata.rapidata_client.benchmark.rapidata_benchmark_manager import RapidataBenchmarkManager

from rapidata.rapidata_client.validation.validation_set_manager import (
    ValidationSetManager,
)

from rapidata.rapidata_client.demographic.demographic_manager import DemographicManager

from rapidata.rapidata_client.logging import logger, managed_print

class RapidataClient:
    """The Rapidata client is the main entry point for interacting with the Rapidata API. It allows you to create orders and validation sets."""

    def __init__(
            self,
            client_id: str | None = None,
            client_secret: str | None = None,
            environment: str = "rapidata.ai",
            oauth_scope: str = "openid",
            cert_path: str | None = None,
            token: dict | None = None,
            leeway: int = 60
    ):
        """Initialize the RapidataClient. If both the client_id and client_secret are None, it will try using your credentials under "~/.config/rapidata/credentials.json".
        If this is not successful, it will open a browser window and ask you to log in, then save your new credentials in said json file.

        Args:
            client_id (str): The client ID for authentication.
            client_secret (str): The client secret for authentication.
            environment (str, optional): The API endpoint.
            oauth_scope (str, optional): The scopes to use for authentication. In general this does not need to be changed.
            cert_path (str, optional): An optional path to a certificate file useful for development.
            token (dict, optional): If you already have a token that the client should use for authentication. Important, if set, this needs to be the complete token object containing the access token, token type and expiration time.
            leeway (int, optional): An optional leeway to use to determine if a token is expired. Defaults to 60 seconds.

        Attributes:
            order (RapidataOrderManager): The RapidataOrderManager instance.
            validation (ValidationSetManager): The ValidationSetManager instance.
        """
        logger.debug("Checking version")
        self._check_version()

        logger.debug("Initializing OpenAPIService")
        self._openapi_service = OpenAPIService(
            client_id=client_id,
            client_secret=client_secret,
            environment=environment,
            oauth_scope=oauth_scope,
            cert_path=cert_path,
            token=token,
            leeway=leeway,
        )

        logger.debug("Initializing RapidataOrderManager")
        self.order = RapidataOrderManager(openapi_service=self._openapi_service)

        logger.debug("Initializing ValidationSetManager")
        self.validation = ValidationSetManager(openapi_service=self._openapi_service)

        logger.debug("Initializing DemographicManager")
        self._demographic = DemographicManager(openapi_service=self._openapi_service)

        logger.debug("Initializing RapidataBenchmarkManager")
        self.mri = RapidataBenchmarkManager(openapi_service=self._openapi_service)
        
    def reset_credentials(self):
        """Reset the credentials saved in the configuration file for the current environment."""
        self._openapi_service.reset_credentials()

    def _check_version(self):
        try:
            response = requests.get(
                "https://api.github.com/repos/RapidataAI/rapidata-python-sdk/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=3
            )
            if response.status_code == 200:
                latest_version = response.json()["tag_name"].lstrip("v")
                if version.parse(latest_version) > version.parse(__version__):
                    managed_print(f"""A new version of the Rapidata SDK is available: {latest_version}
Your current version is: {__version__}""")
        except Exception as e:
            logger.debug(f"Failed to check for updates: {e}")
