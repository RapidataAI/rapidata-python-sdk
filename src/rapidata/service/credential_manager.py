import json
import os
import time
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from socket import gethostname
from typing import Dict, List, Optional, Tuple

import requests
from colorama import Fore
from pydantic import BaseModel
from rapidata.rapidata_client.logging import logger, managed_print


class ClientCredential(BaseModel):
    display_name: str
    client_id: str
    client_secret: str
    endpoint: str
    created_at: datetime
    last_used: datetime

    def get_display_string(self):
        return f"{self.display_name} - Client ID: {self.client_id} (Created: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"


class BridgeToken(BaseModel):
    read_key: str
    write_key: str


class CredentialManager:
    def __init__(
        self,
        endpoint: str,
        cert_path: str | None = None,
        poll_timeout: int = 300,
        poll_interval: int = 1,
    ):
        self.endpoint = endpoint
        self.cert_path = cert_path
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval

        self.config_dir = Path.home() / ".config" / "rapidata"
        self.config_path = self.config_dir / "credentials.json"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _read_credentials(self) -> Dict[str, List[ClientCredential]]:
        """Read all stored credentials from the config file."""
        logger.debug(f"Reading credentials from {self.config_path}")
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
                return {
                    env: [ClientCredential.model_validate(cred) for cred in creds]
                    for env, creds in data.items()
                }
        except json.JSONDecodeError:
            return {}

    def _write_credentials(
        self, credentials: Dict[str, List[ClientCredential]]
    ) -> None:
        data = {
            env: [cred.model_dump(mode="json") for cred in creds]
            for env, creds in credentials.items()
        }

        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Credentials written to {self.config_path} with data: {data}")

        # Ensure file is only readable by the user
        os.chmod(self.config_path, 0o600)
        logger.debug(
            f"Set permissions for {self.config_path} to read/write for user only."
        )

    def _store_credential(self, credential: ClientCredential) -> None:
        credentials = self._read_credentials()

        if credential.endpoint not in credentials:
            credentials[credential.endpoint] = []

        credentials[credential.endpoint].append(credential)
        self._write_credentials(credentials)

    @staticmethod
    def _select_credential(
        credentials: List[ClientCredential],
    ) -> Optional[ClientCredential]:
        if not credentials:
            return None

        if len(credentials) == 1:
            return credentials[0]

        return max(credentials, key=lambda c: c.last_used)

    def get_client_credentials(self) -> Optional[ClientCredential]:
        """Gets stored client credentials or create new ones via browser auth."""
        credentials = self._read_credentials()
        logger.debug(f"Stored credentials: {credentials}")
        env_credentials = credentials.get(self.endpoint, [])

        if env_credentials:
            logger.debug(f"Found credentials for {self.endpoint}: {env_credentials}")
            credential = self._select_credential(env_credentials)
            logger.debug(f"Selected credential: {credential}")
            if credential:
                credential.last_used = datetime.now(timezone.utc)
                self._write_credentials(credentials)
                return credential

        logger.debug(f"No credentials found for {self.endpoint}. Creating new ones.")
        return self._create_new_credentials()

    def reset_credentials(self) -> None:
        """Reset the stored credentials for current environment."""
        credentials = self._read_credentials()
        if self.endpoint in credentials:
            del credentials[self.endpoint]
            self._write_credentials(credentials)
            logger.info(f"Credentials for {self.endpoint} have been reset.")

    def _get_bridge_tokens(self) -> Optional[BridgeToken]:
        """Get bridge tokens from the identity endpoint."""
        logger.debug("Getting bridge tokens")
        try:
            bridge_endpoint = (
                f"{self.endpoint}/identity/bridge-token?clientId=rapidata-cli"
            )
            response = requests.post(bridge_endpoint, verify=self.cert_path)
            if not response.ok:
                logger.error(f"Failed to get bridge tokens: {response.status_code}")
                return None

            data = response.json()
            return BridgeToken(read_key=data["readKey"], write_key=data["writeKey"])
        except requests.RequestException as e:
            logger.error(f"Failed to get bridge tokens: {e}")
            return None

    def _poll_read_key(self, read_key: str) -> Optional[str]:
        """Poll the read key endpoint until we get an access token."""
        read_endpoint = f"{self.endpoint}/identity/bridge-token"
        start_time = time.time()

        while time.time() - start_time < self.poll_timeout:
            try:
                response = requests.get(
                    read_endpoint, params={"readKey": read_key}, verify=self.cert_path
                )

                if response.status_code == 200:
                    return response.json().get("accessToken")
                elif response.status_code == 202:
                    # Still processing
                    time.sleep(self.poll_interval)
                    continue
                else:
                    # Error occurred
                    logger.error(f"Error polling read key: {response.status_code}")
                    return None

            except requests.RequestException as e:
                logger.error(f"Error polling read key: {e}")
                return None

        logger.error("Polling timed out")
        return None

    def _create_client(self, access_token: str) -> Optional[Tuple[str, str, str]]:
        """Create a new client using the access token."""
        try:
            # set the display name to the hostname
            display_name = f"{gethostname()} - Python API Client"
            response = requests.post(
                f"{self.endpoint}/Client",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                },
                json={"displayName": display_name},
                verify=self.cert_path,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("clientId"), data.get("clientSecret"), display_name
        except requests.RequestException as e:
            logger.error(f"Failed to create client: {e}")
            return None

    def _create_new_credentials(self) -> Optional[ClientCredential]:
        bridge_endpoint = self._get_bridge_tokens()
        if not bridge_endpoint:
            return None

        auth_url = f"{self.endpoint}/connect/authorize/external?clientId=rapidata-cli&scope=openid profile email roles&writeKey={bridge_endpoint.write_key}"
        could_open_browser = webbrowser.open(auth_url)

        if not could_open_browser:
            encoded_url = urllib.parse.quote(auth_url, safe="%/:=&?~#+!$,;'@()*[]")
            managed_print(
                Fore.RED
                + f'Please open the following URL in your browser to log in: "{encoded_url}"'
                + Fore.RESET
            )

        access_token = self._poll_read_key(bridge_endpoint.read_key)
        if not access_token:
            return None

        client_state = self._create_client(access_token)

        if not client_state:
            raise ValueError("Failed to create client")

        client_id, client_secret, display_name = client_state

        credential = ClientCredential(
            client_id=client_id,
            client_secret=client_secret,
            display_name=display_name,
            endpoint=self.endpoint,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
        )

        self._store_credential(credential)
        return credential
