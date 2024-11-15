import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable

import requests
from pydantic import BaseModel

from rapidata.service.credential_manager import CredentialManager

logger = logging.getLogger(__name__)


class TokenInfo(BaseModel):
    access_token: str
    expires_in: int
    issued_at: datetime
    token_type: str = "Bearer"

    @property
    def auth_header(self):
        return f"{self.token_type} {self.access_token}"

    @property
    def time_remaining(self):
        remaining = (
            (self.issued_at + timedelta(seconds=self.expires_in)) - datetime.now()
        ).total_seconds()
        return max(0.0, remaining)


class TokenManager:
    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        endpoint: str = "https://auth.rapidata.ai",
        oauth_scope: str = "openid profile email",
        cert_path: str | None = None,
        refresh_threshold: float = 0.8,
        max_sleep_time: float = 30,
    ):
        self._client_id = client_id
        self._client_secret = client_secret

        if not client_id or not client_secret:
            credential_manager = CredentialManager(
                endpoint=endpoint, cert_path=cert_path
            )
            credentials = credential_manager.get_client_credentials()
            if not credentials:
                raise ValueError("Failed to fetch client credentials")
            self._client_id = credentials.client_id
            self._client_secret = credentials.client_secret

        self._endpoint = endpoint
        self._oauth_scope = oauth_scope
        self._cert_path = cert_path
        self._refresh_threshold = refresh_threshold
        self._max_sleep_time = max_sleep_time

        self._token_lock = threading.Lock()
        self._current_token: Optional[TokenInfo] = None
        self._refresh_thread: Optional[threading.Thread] = None
        self._should_stop = threading.Event()

    def fetch_token(self):
        try:
            response = requests.post(
                f"{self._endpoint}/connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": self._oauth_scope,
                },
                verify=self._cert_path,
            )

            if response.ok:
                data = response.json()
                return TokenInfo(
                    access_token=data["access_token"],
                    token_type=data["token_type"],
                    expires_in=data["expires_in"],
                    issued_at=datetime.now(),
                )

            else:
                data = response.text
                error_description = "An unknown error occurred"
                if "error_description" in data:
                    error_description = (
                        data.split("error_description")[1].split("\n")[0].strip()
                    )
                raise ValueError(f"Failed to fetch token: {error_description}")
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch token: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse token response: {e}")
        except KeyError as e:
            raise ValueError(f"Failed to extract token from response: {e}")

    def start_token_refresh(self, token_callback: Callable[[TokenInfo], None]) -> None:
        if self._refresh_thread and self._refresh_thread.is_alive():
            logger.error("Token refresh thread is already running")
            return

        def refresh_loop():
            while not self._should_stop.is_set():
                try:
                    with self._token_lock:
                        if self._should_refresh_token(self._current_token):
                            logger.debug("Refreshing token")
                            self._current_token = self.fetch_token()
                            token_callback(self._current_token)

                    if self._current_token:
                        time_until_refresh_threshold = (
                            self._current_token.time_remaining
                            - (
                                self._current_token.expires_in
                                * (1 - self._refresh_threshold)
                            )
                        )
                        logger.debug("Time until refresh threshold: %s", time_until_refresh_threshold)
                        sleep_time = min(
                            self._max_sleep_time, time_until_refresh_threshold
                        )
                        logger.debug(
                            f"Sleeping for {sleep_time} until checking the token again"
                        )
                        self._should_stop.wait(timeout=max(1.0, sleep_time))
                    else:
                        self._should_stop.wait(timeout=self._max_sleep_time)
                except Exception as e:
                    logger.error("Failed to refresh token: %s", e)
                    self._should_stop.wait(timeout=5)

        self._should_stop.clear()
        self._refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self._refresh_thread.start()

    def stop_token_refresh(self):
        self._should_stop.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=1)
            self._refresh_thread = None

    def get_current_token(self) -> Optional[TokenInfo]:
        with self._token_lock:
            return self._current_token

    def _should_refresh_token(self, token: TokenInfo | None) -> bool:
        if not token:
            return True

        limit = token.expires_in * (1 - self._refresh_threshold)

        logger.debug(
            "The token was issued at %s, it expires in %s. It has %s seconds remaining and we refresh the token when it has %s seconds remaining",
            token.issued_at,
            token.expires_in,
            token.time_remaining,
            limit,
        )
        return token.time_remaining < limit

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_token_refresh()
        return False
