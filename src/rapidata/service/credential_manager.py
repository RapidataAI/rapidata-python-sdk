import base64
import json
import os
import sys
import tempfile
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
from rapidata._agent_hint import detected_coding_agent
from rapidata.rapidata_client.config import logger


class ClientCredential(BaseModel):
    display_name: str
    client_id: str
    client_secret: str
    endpoint: str
    created_at: datetime
    last_used: datetime
    organization_id: Optional[str] = None

    def get_display_string(self):
        organization = (
            f", Organization: {self.organization_id}" if self.organization_id else ""
        )
        return f"{self.display_name} - Client ID: {self.client_id}{organization} (Created: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"


class BridgeToken(BaseModel):
    read_key: str
    write_key: str


class CredentialManager:
    # Per-request HTTP timeout for the bridge/identity endpoints. A
    # (connect, read) pair prevents slow or hung identity servers from
    # pinning the calling thread indefinitely — the outer poll_timeout
    # only caps the total polling loop, not individual requests.
    _HTTP_TIMEOUT: Tuple[float, float] = (10.0, 30.0)

    def __init__(
        self,
        endpoint: str,
        cert_path: str | None = None,
        poll_timeout: int = 300,
        poll_interval: int = 1,
        organization_id: str | None = None,
    ):
        self.endpoint = endpoint
        self.organization_id = organization_id
        self.cert_path = cert_path
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval

        self.config_dir = Path.home() / ".config" / "rapidata"
        self.config_path = self.config_dir / "credentials.json"

        # Ensure config directory exists and is only user-accessible.
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.config_dir, 0o700)
        except OSError as e:
            # Non-fatal on systems that don't support POSIX perms (e.g. Windows).
            logger.debug("Could not tighten permissions on %s: %s", self.config_dir, e)

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

        # A fresh 0o600 temp file per write, then an atomic rename: clients built
        # concurrently in one process each rewrite this file, so a shared temp name races.
        fd, tmp_name = tempfile.mkstemp(
            dir=self.config_dir, prefix=f"{self.config_path.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            # Re-assert perms in case umask or NFS stripped them.
            try:
                os.chmod(tmp_path, 0o600)
            except OSError:
                pass
            os.replace(tmp_path, self.config_path)
        except Exception:
            # Best-effort cleanup of the temp file on any error.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # NOTE: do NOT log the credential payload — client_secret values
        # are long-lived OAuth secrets and must never leave the file.
        # The atomic rename above already establishes 0o600 from creation,
        # so no trailing chmod is needed.
        logger.debug(
            "Credentials written to %s (%d environment(s), %d credential(s))",
            self.config_path,
            len(data),
            sum(len(creds) for creds in data.values()),
        )

    def _store_credential(self, credential: ClientCredential) -> None:
        credentials = self._read_credentials()

        if credential.endpoint not in credentials:
            credentials[credential.endpoint] = []

        credentials[credential.endpoint].append(credential)
        self._write_credentials(credentials)

    def _matches(self, credential: ClientCredential) -> bool:
        # Without a pinned organization any credential of the environment is usable, legacy org-less ones included.
        return (
            self.organization_id is None
            or credential.organization_id == self.organization_id
        )

    def _select_credential(
        self,
        credentials: List[ClientCredential],
    ) -> Optional[ClientCredential]:
        candidates = [c for c in credentials if self._matches(c)]
        if not candidates:
            return None

        return max(candidates, key=lambda c: c.last_used)

    def stored_credential(self) -> Optional[ClientCredential]:
        """Return the credential saved for this endpoint and organization without starting a login."""
        return self._select_credential(self._read_credentials().get(self.endpoint, []))

    def get_client_credentials(self) -> Optional[ClientCredential]:
        """Gets stored client credentials or create new ones via browser auth."""
        credentials = self._read_credentials()
        logger.debug("Stored credentials: %s", credentials)
        credential = self._select_credential(credentials.get(self.endpoint, []))
        logger.debug("Selected credential: %s", credential)
        if credential:
            credential.last_used = datetime.now(timezone.utc)
            self._write_credentials(credentials)
            return credential

        logger.debug(
            "No credentials found for %s (organization %s). Creating new ones.",
            self.endpoint,
            self.organization_id,
        )
        return self._create_new_credentials()

    def reset_credentials(self) -> None:
        """Reset the stored credentials for the current environment and organization."""
        credentials = self._read_credentials()
        if self.endpoint not in credentials:
            return
        kept = [c for c in credentials[self.endpoint] if not self._matches(c)]
        if kept:
            credentials[self.endpoint] = kept
        else:
            del credentials[self.endpoint]
        self._write_credentials(credentials)
        logger.info(
            "Credentials for %s (organization %s) have been reset.",
            self.endpoint,
            self.organization_id,
        )

    def _get_bridge_tokens(self) -> Optional[BridgeToken]:
        """Get bridge tokens from the identity endpoint."""
        logger.debug("Getting bridge tokens")
        try:
            bridge_endpoint = (
                f"{self.endpoint}/identity/bridge-token?clientId=rapidata-cli"
            )
            response = requests.post(
                bridge_endpoint,
                verify=self.cert_path,
                timeout=self._HTTP_TIMEOUT,
            )
            if not response.ok:
                logger.error("Failed to get bridge tokens: %s", response.status_code)
                return None

            data = response.json()
        except requests.RequestException as e:
            logger.error("Failed to get bridge tokens: %s", e)
            return None
        except ValueError as e:
            # `response.json()` raises ValueError on malformed bodies.
            logger.error("Bridge token response was not valid JSON: %s", e)
            return None

        try:
            return BridgeToken(read_key=data["readKey"], write_key=data["writeKey"])
        except (KeyError, TypeError) as e:
            logger.error(
                "Bridge token response missing expected keys (got: %s): %s",
                list(data.keys()) if isinstance(data, dict) else type(data).__name__,
                e,
            )
            return None

    def _print_login_prompt(self, auth_url: str, opened_browser: bool) -> None:
        """Print the login URL, flushed to stderr and ignoring silent mode, so a coding agent can relay it."""
        encoded_url = urllib.parse.quote(auth_url, safe="%/:=&?~#+!$,;'@()*[]")
        lead = (
            "Log in to Rapidata in the browser window that just opened, or open this URL:"
            if opened_browser
            else "Open this URL in your browser to log in to Rapidata:"
        )
        lines = [Fore.RED + lead + Fore.RESET, f"  {encoded_url}"]
        if detected_coding_agent():
            lines.append(
                f"Coding agent: show this URL to the user and ask them to log in. "
                f"This call waits up to {self.poll_timeout // 60} minutes; once they "
                f"are logged in, later runs reuse the saved credentials."
            )
        print("\n".join(lines), file=sys.stderr, flush=True)

    def _poll_read_key(self, read_key: str) -> Optional[str]:
        """Poll the read key endpoint until we get an access token."""
        read_endpoint = f"{self.endpoint}/identity/bridge-token"
        start_time = time.time()

        while time.time() - start_time < self.poll_timeout:
            try:
                response = requests.get(
                    read_endpoint,
                    params={"readKey": read_key},
                    verify=self.cert_path,
                    timeout=self._HTTP_TIMEOUT,
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

    def _create_client(
        self, access_token: str
    ) -> Optional[Tuple[str, str, str, Optional[str]]]:
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
                timeout=self._HTTP_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return (
                data.get("clientId"),
                data.get("clientSecret"),
                display_name,
                data.get("organizationId"),
            )
        except requests.RequestException as e:
            logger.error("Failed to create client: %s", e)
            return None

    @staticmethod
    def _token_organization(access_token: str) -> Optional[str]:
        """Read the unverified `org` claim; it only labels the stored credential, identity enforces it."""
        try:
            payload = access_token.split(".")[1]
            claims = json.loads(
                base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            )
        except (IndexError, ValueError) as e:
            logger.debug("Could not read the organization of the access token: %s", e)
            return None
        organization = claims.get("org") if isinstance(claims, dict) else None
        return organization if isinstance(organization, str) else None

    def _auth_url(self, write_key: str) -> str:
        auth_url = f"{self.endpoint}/connect/authorize/external?clientId=rapidata-cli&scope=openid profile email api&writeKey={write_key}"
        if self.organization_id:
            auth_url += (
                f"&organization={urllib.parse.quote(self.organization_id, safe='')}"
            )
        return auth_url

    def _create_new_credentials(self) -> Optional[ClientCredential]:
        bridge_endpoint = self._get_bridge_tokens()
        if not bridge_endpoint:
            return None

        auth_url = self._auth_url(bridge_endpoint.write_key)
        could_open_browser = webbrowser.open(auth_url)
        self._print_login_prompt(auth_url, could_open_browser)

        access_token = self._poll_read_key(bridge_endpoint.read_key)
        if not access_token:
            return None

        # Refuse before POST /Client so a login that landed elsewhere creates no key there.
        token_organization = self._token_organization(access_token)
        if self.organization_id and token_organization != self.organization_id:
            raise ValueError(
                f"Logged in to organization {token_organization}, but organization {self.organization_id} was requested. "
                "Log in again and pick that organization on the login page."
            )

        client_state = self._create_client(access_token)

        if not client_state:
            raise ValueError("Failed to create client")

        client_id, client_secret, display_name, organization_id = client_state
        organization_id = organization_id or token_organization

        credential = ClientCredential(
            client_id=client_id,
            client_secret=client_secret,
            display_name=display_name,
            endpoint=self.endpoint,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            organization_id=organization_id,
        )

        self._store_credential(credential)
        return credential
