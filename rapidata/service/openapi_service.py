from openapi_client.api.dataset_api import DatasetApi
from openapi_client.api.identity_api import IdentityApi
from openapi_client.api.order_api import OrderApi
from openapi_client.api_client import ApiClient
from openapi_client.configuration import Configuration


class OpenAPIService:

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str = "https://api.rapidata.ai",
    ):
        client_configuration = Configuration(host=endpoint)
        self.api_client = ApiClient(configuration=client_configuration)

        identity_api = IdentityApi(self.api_client)

        result = identity_api.identity_get_client_auth_token_post(
            client_id=client_id,
            _headers={"Authorization": f"Basic {client_secret}"},
        )

        client_configuration.api_key["bearer"] = f"Bearer {result.auth_token}"
        self._api_client = ApiClient()
        self._order_api = OrderApi(self.api_client)
        self._dataset_api = DatasetApi(self.api_client)

    @property
    def order_api(self) -> OrderApi:
        return self._order_api

    @property
    def dataset_api(self) -> DatasetApi:
        return self._dataset_api