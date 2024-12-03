from rapidata.api_client.api.campaign_api import CampaignApi
from rapidata.api_client.api.dataset_api import DatasetApi
from rapidata.api_client.api.order_api import OrderApi
from rapidata.api_client.api.pipeline_api import PipelineApi
from rapidata.api_client.api.rapid_api import RapidApi
from rapidata.api_client.api.validation_api import ValidationApi
from rapidata.api_client.api.workflow_api import WorkflowApi
from rapidata.api_client.api_client import ApiClient
from rapidata.api_client.configuration import Configuration
from rapidata.service.token_manager import TokenManager, TokenInfo

from importlib.metadata import version, PackageNotFoundError


class OpenAPIService:
    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        enviroment: str,
        oauth_scope: str,
        cert_path: str | None = None,
    ):
        self.enviroment = enviroment
        endpoint = f"https://api.{enviroment}"
        token_url = f"https://auth.{enviroment}"
        token_manager = TokenManager(
            client_id=client_id,
            client_secret=client_secret,
            endpoint=token_url,
            oauth_scope=oauth_scope,
            cert_path=cert_path,
        )
        client_configuration = Configuration(host=endpoint, ssl_ca_cert=cert_path)
        self.api_client = ApiClient(
            configuration=client_configuration,
            header_name="X-Client",
            header_value=f"RapidataPythonSDK/{self._get_rapidata_package_version()}",
        )

        self.api_client.configuration.api_key["bearer"] = (
            f"Bearer {token_manager.fetch_token().access_token}"
        )

        self._client_id = client_id
        self._client_secret = client_secret
        self._oauth_scope = oauth_scope
        self._token_url = f"{token_url}/connect/token"
        self._cert_path = cert_path

        token_manager.start_token_refresh(token_callback=self._set_token)

    @property
    def order_api(self) -> OrderApi:
        return OrderApi(self.api_client)

    @property
    def dataset_api(self) -> DatasetApi:
        return DatasetApi(self.api_client)

    @property
    def validation_api(self) -> ValidationApi:
        return ValidationApi(self.api_client)

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

    def _set_token(self, token: TokenInfo):
        self.api_client.configuration.api_key["bearer"] = f"Bearer {token.access_token}"

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
