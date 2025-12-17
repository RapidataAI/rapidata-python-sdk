from __future__ import annotations

import subprocess
from importlib.metadata import version, PackageNotFoundError
from typing import TYPE_CHECKING

from rapidata.api_client.configuration import Configuration
from rapidata.service.credential_manager import CredentialManager
from rapidata.rapidata_client.api.rapidata_api_client import RapidataApiClient
from rapidata.rapidata_client.config import logger, managed_print
from authlib.integrations.httpx_client import OAuthError

if TYPE_CHECKING:
    from rapidata.api_client.api.job_api import JobApi
    from rapidata.api_client import CustomerRapidApi
    from rapidata.api_client.api.campaign_api import CampaignApi
    from rapidata.api_client.api.asset_api import AssetApi
    from rapidata.api_client.api.dataset_api import DatasetApi
    from rapidata.api_client.api.benchmark_api import BenchmarkApi
    from rapidata.api_client.api.order_api import OrderApi
    from rapidata.api_client.api.pipeline_api import PipelineApi
    from rapidata.api_client.api.leaderboard_api import LeaderboardApi
    from rapidata.api_client.api.validation_set_api import ValidationSetApi
    from rapidata.api_client.api.workflow_api import WorkflowApi
    from rapidata.api_client.api.participant_api import ParticipantApi
    from rapidata.api_client.api.audience_api import AudienceApi


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

        logger.debug(
            "Using cert_path: %s environment: %s client_id: %s",
            cert_path,
            environment,
            client_id,
        )
        logger.debug("Initializing OpenAPIService")
        self.credential_manager = CredentialManager(
            endpoint=auth_endpoint, cert_path=cert_path
        )
        logger.debug("CredentialManager initialized")

        logger.debug("Initializing RapidataApiClient")
        client_configuration = Configuration(host=endpoint, ssl_ca_cert=cert_path)
        logger.debug("Client configuration: %s", client_configuration)
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
            logger.debug(
                "Client ID and secret not provided, fetching from credential manager"
            )
            credentials = self.credential_manager.get_client_credentials()
            if not credentials:
                raise ValueError("Failed to fetch client credentials")
            client_id = credentials.client_id
            client_secret = credentials.client_secret
        try:
            self.api_client.rest_client.setup_oauth_client_credentials(
                client_id=client_id,
                client_secret=client_secret,
                token_endpoint=f"{auth_endpoint}/connect/token",
                scope=oauth_scope,
            )
        except OAuthError as e:
            if e.error != "invalid_client":
                raise
            logger.warning(
                "Invalid client credentials detected, resetting and retrying: %s", e
            )
            self.reset_credentials()

            # Retry with fresh credentials
            credentials = self.credential_manager.get_client_credentials()
            if not credentials:
                raise ValueError(
                    "Failed to fetch client credentials after reset"
                ) from e

            self.api_client.rest_client.setup_oauth_client_credentials(
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
                token_endpoint=f"{auth_endpoint}/connect/token",
                scope=oauth_scope,
            )
            managed_print("Credentials were reset and re-authenticated successfully")

        logger.debug("Client credentials authentication setup complete")

    def reset_credentials(self):
        logger.info("Resetting credentials in OpenAPIService")
        self.credential_manager.reset_credentials()
        logger.info("Credentials reset in OpenAPIService")

    @property
    def order_api(self) -> OrderApi:
        from rapidata.api_client.api.order_api import OrderApi

        return OrderApi(self.api_client)

    @property
    def job_api(self) -> JobApi:
        from rapidata.api_client.api.job_api import JobApi

        return JobApi(self.api_client)

    @property
    def asset_api(self) -> AssetApi:
        from rapidata.api_client.api.asset_api import AssetApi

        return AssetApi(self.api_client)

    @property
    def dataset_api(self) -> DatasetApi:
        from rapidata.api_client.api.dataset_api import DatasetApi

        return DatasetApi(self.api_client)

    @property
    def validation_api(self) -> ValidationSetApi:
        from rapidata.api_client.api.validation_set_api import ValidationSetApi

        return ValidationSetApi(self.api_client)

    @property
    def rapid_api(self) -> CustomerRapidApi:
        from rapidata.api_client.api.customer_rapid_api import CustomerRapidApi

        return CustomerRapidApi(self.api_client)

    @property
    def campaign_api(self) -> CampaignApi:
        from rapidata.api_client.api.campaign_api import CampaignApi

        return CampaignApi(self.api_client)

    @property
    def pipeline_api(self) -> PipelineApi:
        from rapidata.api_client.api.pipeline_api import PipelineApi

        return PipelineApi(self.api_client)

    @property
    def workflow_api(self) -> WorkflowApi:
        from rapidata.api_client.api.workflow_api import WorkflowApi

        return WorkflowApi(self.api_client)

    @property
    def leaderboard_api(self) -> LeaderboardApi:
        from rapidata.api_client.api.leaderboard_api import LeaderboardApi

        return LeaderboardApi(self.api_client)

    @property
    def benchmark_api(self) -> BenchmarkApi:
        from rapidata.api_client.api.benchmark_api import BenchmarkApi

        return BenchmarkApi(self.api_client)

    @property
    def participant_api(self) -> ParticipantApi:
        from rapidata.api_client.api.participant_api import ParticipantApi

        return ParticipantApi(self.api_client)

    @property
    def audience_api(self) -> AudienceApi:
        from rapidata.api_client.api.audience_api import AudienceApi

        return AudienceApi(self.api_client)

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

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"OpenAPIService(environment={self.environment})"


def _get_local_certificate() -> str | None:
    result = subprocess.run(["mkcert", "-CAROOT"], capture_output=True)
    if result.returncode != 0:
        return None

    output = result.stdout.decode("utf-8").strip()
    if not output:
        return None

    return f"{output}/rootCA.pem"
