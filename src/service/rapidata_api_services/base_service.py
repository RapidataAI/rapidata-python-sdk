from datetime import datetime, timedelta, timezone
import jwt
import requests


class BaseRapidataAPIService:

    def __init__(self, client_id: str, client_secret: str, endpoint: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoint = endpoint
        self.token = self._get_auth_token()

    def _check_response(self, response: requests.Response):
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} - {response.text}")

    def _get_new_auth_token_if_outdated(self):
        if not self.token or not self._is_token_valid():
            self._get_auth_token()

    def _is_token_valid(self, expiration_threshold: timedelta = timedelta(minutes=5)):
        try:
            payload = jwt.decode(self.token, options={"verify_signature": False})  # type: ignore
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                expiration_time = datetime.fromtimestamp(exp_timestamp)
                return (
                    datetime.now(timezone.utc) + expiration_threshold <= expiration_time
                )
        except jwt.DecodeError:
            return False
        return False

    def _get_auth_token(self):
        url = f"{self.endpoint}/Login/GetClientAuthToken"
        params = {
            "clientId": self.client_id,
        }
        headers = {"Authorization": f"Basic {self.client_secret}"}
        response = requests.post(url, params=params, headers=headers)
        self._check_response(response)
        self.token = response.json().get("authToken")
        if not self.token:
            raise Exception("No token received")
        self.auth_header = {"Authorization": f"Bearer {self.token}"}
