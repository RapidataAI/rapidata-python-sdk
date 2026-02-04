import json
import os
import time
import urllib.parse
import webbrowser
import platform
from datetime import datetime, timezone
from pathlib import Path
from socket import gethostname
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import Fore
from pydantic import BaseModel
from rapidata.rapidata_client.config import logger, managed_print

# Import platform-specific file locking
if platform.system() == "Windows":
    import msvcrt
else:
    import fcntl


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

        # Create session with connection pooling and retry logic
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a session with connection pooling and retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],  # Retry on both GET and POST
        )

        # Mount adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools
            pool_maxsize=10,  # Connections per pool
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def close(self) -> None:
        """Close the session and cleanup resources."""
        if self._session:
            self._session.close()

    def __enter__(self):
        """Support context manager usage."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when exiting context manager."""
        self.close()
        return False

    def _lock_file(self, file_handle):
        """
        Acquire an exclusive lock on the file.
        Works cross-platform (Unix and Windows).
        """
        if platform.system() == "Windows":
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)

    def _unlock_file(self, file_handle):
        """
        Release the lock on the file.
        Works cross-platform (Unix and Windows).
        """
        if platform.system() == "Windows":
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)

    def _read_credentials(self) -> Dict[str, List[ClientCredential]]:
        """Read all stored credentials from the config file."""
        logger.debug("Reading credentials from %s", self.config_path)
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

        logger.debug("Credentials written to %s with data: %s", self.config_path, data)

        # Ensure file is only readable by the user
        os.chmod(self.config_path, 0o600)
        logger.debug(
            "Set permissions for %s to read/write for user only.", self.config_path
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
        # Create a lock file to prevent multiple processes from creating credentials simultaneously
        lock_file_path = self.config_dir / "credentials.lock"

        with open(lock_file_path, "w") as lock_file:
            try:
                # Acquire exclusive lock
                self._lock_file(lock_file)

                # Re-read credentials after acquiring lock (another process might have created them)
                credentials = self._read_credentials()
                logger.debug("Stored credentials: %s", credentials)
                env_credentials = credentials.get(self.endpoint, [])

                if env_credentials:
                    logger.debug("Found credentials for %s: %s", self.endpoint, env_credentials)
                    credential = self._select_credential(env_credentials)
                    logger.debug("Selected credential: %s", credential)
                    if credential:
                        credential.last_used = datetime.now(timezone.utc)
                        self._write_credentials(credentials)
                        return credential

                logger.debug("No credentials found for %s. Creating new ones.", self.endpoint)
                return self._create_new_credentials()
            finally:
                # Release lock
                self._unlock_file(lock_file)

    def reset_credentials(self) -> None:
        """Reset the stored credentials for current environment."""
        credentials = self._read_credentials()
        if self.endpoint in credentials:
            del credentials[self.endpoint]
            self._write_credentials(credentials)
            logger.info("Credentials for %s have been reset.", self.endpoint)

    def _get_bridge_tokens(self) -> Optional[BridgeToken]:
        """Get bridge tokens from the identity endpoint."""
        logger.debug("Getting bridge tokens")
        try:
            bridge_endpoint = (
                f"{self.endpoint}/identity/bridge-token?clientId=rapidata-cli"
            )
            response = self._session.post(
                bridge_endpoint, verify=self.cert_path, timeout=(5, 30)
            )
            if not response.ok:
                logger.error("Failed to get bridge tokens: %s", response.status_code)
                return None

            data = response.json()
            return BridgeToken(read_key=data["readKey"], write_key=data["writeKey"])
        except requests.RequestException as e:
            logger.error("Failed to get bridge tokens: %s", e)
            return None

    def _poll_read_key(self, read_key: str) -> Optional[str]:
        """Poll the read key endpoint until we get an access token."""
        read_endpoint = f"{self.endpoint}/identity/bridge-token"
        start_time = time.time()

        while time.time() - start_time < self.poll_timeout:
            try:
                response = self._session.get(
                    read_endpoint,
                    params={"readKey": read_key},
                    verify=self.cert_path,
                    timeout=(5, 30),
                )

                if response.status_code == 200:
                    return response.json().get("accessToken")
                elif response.status_code == 202:
                    # Still processing
                    time.sleep(self.poll_interval)
                    continue
                else:
                    # Error occurred
                    logger.error("Error polling read key: %s", response.status_code)
                    return None

            except requests.RequestException as e:
                logger.error("Error polling read key: %s", e)
                return None

        logger.error("Polling timed out")
        return None

    def _create_client(self, access_token: str) -> Optional[Tuple[str, str, str]]:
        """Create a new client using the access token."""
        try:
            # set the display name to the hostname
            display_name = f"{gethostname()} - Python API Client"
            response = self._session.post(
                f"{self.endpoint}/Client",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "*/*",
                },
                json={"displayName": display_name},
                verify=self.cert_path,
                timeout=(5, 30),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("clientId"), data.get("clientSecret"), display_name
        except requests.RequestException as e:
            logger.error("Failed to create client: %s", e)
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
