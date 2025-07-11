import subprocess
from importlib.metadata import version, PackageNotFoundError

from rapidata.api_client.api.campaign_api import CampaignApi
from rapidata.api_client.api.dataset_api import DatasetApi
from rapidata.api_client.api.benchmark_api import BenchmarkApi
from rapidata.api_client.api.order_api import OrderApi
from rapidata.api_client.api.pipeline_api import PipelineApi
from rapidata.api_client.api.rapid_api import RapidApi
from rapidata.api_client.api.leaderboard_api import LeaderboardApi
from rapidata.api_client.api.validation_set_api import ValidationSetApi
from rapidata.api_client.api.workflow_api import WorkflowApi
from rapidata.api_client.configuration import Configuration
from rapidata.service.credential_manager import CredentialManager
from rapidata.rapidata_client.api.rapidata_exception import RapidataApiClient
from rapidata.rapidata_client.logging import logger


class OpenAPIService:
    def __init__(
            self,
            client_id: str | None,
            client_secret: str | None,
            environment: str,
            oauth_scope: str,
            cert_path: str | None = None,
            token: dict | None = None,
            leeway: int = 60,
    ):
        self.environment = environment
        endpoint = f"https://api.{environment}"
        auth_endpoint = f"https://auth.{environment}"

        if environment == "rapidata.dev" and not cert_path:
            cert_path = _get_local_certificate()

        logger.debug(f"Using cert_path: {cert_path} environment: {environment} token: {token} client_id: {client_id} client_secret: {client_secret}")
        logger.debug("Initializing OpenAPIService")
        self.credential_manager = CredentialManager(
            endpoint=auth_endpoint, cert_path=cert_path
        )
        logger.debug("CredentialManager initialized")

        logger.debug("Initializing RapidataApiClient")
        client_configuration = Configuration(host=endpoint, ssl_ca_cert=cert_path)
        logger.debug(f"Client configuration: {client_configuration}")
        self.api_client = RapidataApiClient(
            configuration=client_configuration,
            header_name="X-Client",
            header_value=f"RapidataPythonSDK/{self._get_rapidata_package_version()}",
        )
        logger.debug("RapidataApiClient initialized")

        if token:
            logger.debug("Using token for authentication")
            self.api_client.rest_client.setup_oauth_with_token(
                token=token,
                token_endpoint=f"{auth_endpoint}/connect/token",
                client_id=client_id,
                client_secret=client_secret,
                leeway=leeway,
            )
            logger.debug("Token authentication setup complete")
            return

        if not client_id or not client_secret:
            logger.debug("Client ID and secret not provided, fetching from credential manager")
            credentials = self.credential_manager.get_client_credentials()
            if not credentials:
                raise ValueError("Failed to fetch client credentials")
            client_id = credentials.client_id
            client_secret = credentials.client_secret

        self.api_client.rest_client.setup_oauth_client_credentials(
            client_id=client_id,
            client_secret=client_secret,
            token_endpoint=f"{auth_endpoint}/connect/token",
            scope=oauth_scope,
        )
        logger.debug("Client credentials authentication setup complete")

    def reset_credentials(self):
        self.credential_manager.reset_credentials()

    @property
    def order_api(self) -> OrderApi:
        return OrderApi(self.api_client)

    @property
    def dataset_api(self) -> DatasetApi:
        return DatasetApi(self.api_client)

    @property
    def validation_api(self) -> ValidationSetApi:
        return ValidationSetApi(self.api_client)

    @property
    def rapid_api(self) -> RapidApi:
        return RapidApi(self.api_client)

    @property
    def campaign_api(self) -> CampaignApi:
        return CampaignApi(self.api_client)

    @property
    def pipeline_api(self) -> PipelineApi:
        return PipelineApi(self.api_client)

    @property
    def workflow_api(self) -> WorkflowApi:
        return WorkflowApi(self.api_client)
    
    @property
    def leaderboard_api(self) -> LeaderboardApi:
        return LeaderboardApi(self.api_client)
    
    @property
    def benchmark_api(self) -> BenchmarkApi:
        return BenchmarkApi(self.api_client)

    def _get_rapidata_package_version(self):
        """
        Returns the version of the currently installed rapidata package.

        Returns:
            Optional[str]: The version of the installed rapidata package,
                        or None if the package is not found
        """
        try:
            return version("rapidata")
        except PackageNotFoundError:
            return None


def _get_local_certificate() -> str | None:
    result = subprocess.run(["mkcert", "-CAROOT"], capture_output=True)
    if result.returncode != 0:
        return None

    output = result.stdout.decode("utf-8").strip()
    if not output:
        return None

    return f"{output}/rootCA.pem"
