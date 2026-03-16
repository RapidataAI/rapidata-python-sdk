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
    from rapidata.service.services.asset_service import AssetService
    from rapidata.service.services.order_service import OrderService
    from rapidata.service.services.flow_service import FlowService
    from rapidata.service.services.audience_service import AudienceService
    from rapidata.service.services.validation_service import ValidationService
    from rapidata.service.services.dataset_service import DatasetService
    from rapidata.service.services.campaign_service import CampaignService
    from rapidata.service.services.pipeline_service import PipelineService
    from rapidata.service.services.workflow_service import WorkflowService
    from rapidata.service.services.leaderboard_service import LeaderboardService
    from rapidata.service.services.rapid_service import RapidService


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

        self._asset: AssetService | None = None
        self._order: OrderService | None = None
        self._flow: FlowService | None = None
        self._audience: AudienceService | None = None
        self._validation: ValidationService | None = None
        self._dataset: DatasetService | None = None
        self._campaign: CampaignService | None = None
        self._pipeline: PipelineService | None = None
        self._workflow: WorkflowService | None = None
        self._leaderboard: LeaderboardService | None = None
        self._rapid: RapidService | None = None

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
    def asset(self) -> AssetService:
        if self._asset is None:
            from rapidata.service.services.asset_service import AssetService
            self._asset = AssetService(self.api_client)
        return self._asset

    @property
    def order(self) -> OrderService:
        if self._order is None:
            from rapidata.service.services.order_service import OrderService
            self._order = OrderService(self.api_client)
        return self._order

    @property
    def flow(self) -> FlowService:
        if self._flow is None:
            from rapidata.service.services.flow_service import FlowService
            self._flow = FlowService(self.api_client)
        return self._flow

    @property
    def audience(self) -> AudienceService:
        if self._audience is None:
            from rapidata.service.services.audience_service import AudienceService
            self._audience = AudienceService(self.api_client)
        return self._audience

    @property
    def validation(self) -> ValidationService:
        if self._validation is None:
            from rapidata.service.services.validation_service import ValidationService
            self._validation = ValidationService(self.api_client)
        return self._validation

    @property
    def dataset(self) -> DatasetService:
        if self._dataset is None:
            from rapidata.service.services.dataset_service import DatasetService
            self._dataset = DatasetService(self.api_client)
        return self._dataset

    @property
    def campaign(self) -> CampaignService:
        if self._campaign is None:
            from rapidata.service.services.campaign_service import CampaignService
            self._campaign = CampaignService(self.api_client)
        return self._campaign

    @property
    def pipeline(self) -> PipelineService:
        if self._pipeline is None:
            from rapidata.service.services.pipeline_service import PipelineService
            self._pipeline = PipelineService(self.api_client)
        return self._pipeline

    @property
    def workflow(self) -> WorkflowService:
        if self._workflow is None:
            from rapidata.service.services.workflow_service import WorkflowService
            self._workflow = WorkflowService(self.api_client)
        return self._workflow

    @property
    def leaderboard(self) -> LeaderboardService:
        if self._leaderboard is None:
            from rapidata.service.services.leaderboard_service import LeaderboardService
            self._leaderboard = LeaderboardService(self.api_client)
        return self._leaderboard

    @property
    def rapid(self) -> RapidService:
        if self._rapid is None:
            from rapidata.service.services.rapid_service import RapidService
            self._rapid = RapidService(self.api_client)
        return self._rapid

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
