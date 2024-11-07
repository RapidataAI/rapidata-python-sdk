import json
import time
import requests
import threading
from rapidata.api_client.api.campaign_api import CampaignApi
from rapidata.api_client.api.dataset_api import DatasetApi
from rapidata.api_client.api.order_api import OrderApi
from rapidata.api_client.api.pipeline_api import PipelineApi
from rapidata.api_client.api.rapid_api import RapidApi
from rapidata.api_client.api.validation_api import ValidationApi
from rapidata.api_client.api.workflow_api import WorkflowApi
from rapidata.api_client.api_client import ApiClient
from rapidata.api_client.configuration import Configuration


class OpenAPIService:

    _TOKEN_EXPIRATION_MINUTES = 30

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str,
        token_url: str,
        oauth_scope: str,
        cert_path: str | None = None
    ):
        client_configuration = Configuration(host=endpoint, ssl_ca_cert=cert_path)
        self.api_client = ApiClient(configuration=client_configuration)

        self._client_id = client_id
        self._client_secret = client_secret
        self._oauth_scope = oauth_scope
        self._token_url = token_url
        self._cert_path = cert_path

        self._api_client = ApiClient()
        self._order_api = OrderApi(self.api_client)
        self._dataset_api = DatasetApi(self.api_client)

        api_token = self.__fetch_token(
            self._client_id, self._client_secret, self._oauth_scope, self._token_url, self._cert_path
        )
        self.api_client.configuration.api_key["bearer"] = f"Bearer {api_token}"

        refresh_thread = threading.Thread(
            target=lambda: self.__refresh_token_periodically(self._TOKEN_EXPIRATION_MINUTES - 1)
        )
        refresh_thread.daemon = True
        refresh_thread.start()

    def __refresh_token_periodically(self, refresh_interval):
        while True:
            new_token = self.__fetch_token(
                self._client_id, self._client_secret, self._oauth_scope, self._token_url, self._cert_path
            )
            self.api_client.configuration.api_key["bearer"] = f"Bearer {new_token}"

            time.sleep(refresh_interval)

    @property
    def order_api(self) -> OrderApi:
        return self._order_api

    @property
    def dataset_api(self) -> DatasetApi:
        return self._dataset_api

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

    @staticmethod
    def __fetch_token(client_id: str, client_secret: str, scope: str, token_url: str, cert_path: str | None = None) -> str:
        try:
            return requests.post(
                token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'scope': scope,
                },
                verify=cert_path
            ).json()['access_token']
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch token: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse token response: {e}")
        except KeyError as e:
            raise Exception(f"Failed to extract token from response: {e}")

