from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any
import requests
from packaging import version
from rapidata import __version__
import uuid
import random
from rapidata.service.openapi_service import OpenAPIService

from rapidata.rapidata_client.benchmark.rapidata_benchmark_manager import (
    RapidataBenchmarkManager,
)
from rapidata.rapidata_client.audience.rapidata_audience_manager import (
    RapidataAudienceManager,
)
from rapidata.rapidata_client.order.rapidata_order_manager import RapidataOrderManager
from rapidata.rapidata_client.validation.validation_set_manager import (
    ValidationSetManager,
)

from rapidata.rapidata_client.demographic.demographic_manager import DemographicManager
from rapidata.rapidata_client.context.context_manager import ContextManager

from rapidata.rapidata_client.config import (
    logger,
    tracer,
    managed_print,
    rapidata_config,
)

from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.job.rapidata_job_manager import RapidataJobManager
from rapidata.rapidata_client.flow.rapidata_flow_manager import RapidataFlowManager
from rapidata.rapidata_client.signal.rapidata_signal_manager import (
    RapidataSignalManager,
)
from rapidata.rapidata_client.api.rapidata_api_client import (
    optional_api_call,
    mark_sdk_outdated,
)


# Cache userinfo process-wide so request bursts that spin up many short-lived
# RapidataClient instances don't hammer identity-service with redundant calls.
@dataclass
class _UserInfoCacheEntry:
    result: dict[str, Any]
    expires_at: float


_USERINFO_CACHE_TTL_SECONDS = 24 * 60 * 60
_userinfo_cache: dict[tuple[str, str], _UserInfoCacheEntry] = {}
_userinfo_cache_lock = threading.Lock()

# Environments with a deployed SDK OTLP collector at otlp-sdk.<environment>.
# Other environments (e.g. local rapidata.dev) have no collector, so OTLP is
# left disabled there to avoid noisy failed exports.
_OTLP_COLLECTOR_ENVIRONMENTS = frozenset({"rapidata.ai", "rabbitdata.ch"})


class RapidataClient:
    """The Rapidata client is the main entry point for interacting with the Rapidata API. It allows you to create orders and validation sets."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        environment: str | None = None,
        oauth_scope: str = "openid roles email api",
        cert_path: str | None = None,
        token: dict | None = None,
        token_file: str | None = None,
        leeway: int = 60,
    ):
        """Initialize the RapidataClient.

        Credentials are resolved in the following order:

        1. A ``token`` or ``token_file`` passed explicitly to this
           constructor (or the ``RAPIDATA_TOKEN_FILE`` environment
           variable), which bypasses the token exchange entirely.
        2. ``client_id`` / ``client_secret`` passed explicitly to this
           constructor.
        3. The ``RAPIDATA_CLIENT_ID`` / ``RAPIDATA_CLIENT_SECRET``
           environment variables (useful for headless / container
           deployments).
        4. Credentials stored under ``~/.config/rapidata/credentials.json``.
        5. Interactive browser login, which then saves credentials to the
           file above so you don't have to log in again.

        The ``environment`` argument follows the same pattern: when omitted
        it falls back to the ``RAPIDATA_ENVIRONMENT`` environment variable,
        and finally to the default ``"rapidata.ai"``.

        Args:
            client_id (str): The client ID for authentication. Falls back to
                the ``RAPIDATA_CLIENT_ID`` environment variable when omitted.
            client_secret (str): The client secret for authentication. Falls
                back to the ``RAPIDATA_CLIENT_SECRET`` environment variable
                when omitted.
            environment (str, optional): The API endpoint. Falls back to the
                ``RAPIDATA_ENVIRONMENT`` environment variable, and then to
                ``"rapidata.ai"``.
            oauth_scope (str, optional): The scopes to use for authentication. In general this does not need to be changed.
            cert_path (str, optional): An optional path to a certificate file useful for development.
            token (dict, optional): If you already have a token that the client should use for authentication. Important, if set, this needs to be the complete token object containing the access token, token type and expiration time.
            token_file (str, optional): Path to a JSON file containing the token object described above (with an absolute ``expires_at`` timestamp). The file is re-read whenever the current token expires, so an external process can keep it fresh — useful to share one token across many workers (e.g. distributed training). Falls back to the ``RAPIDATA_TOKEN_FILE`` environment variable when omitted.
            leeway (int, optional): How many seconds before its actual expiry a token is treated as expired — i.e. how early it is refreshed (or re-read from ``token_file``). Defaults to 60 seconds.

        Attributes:
            order (RapidataOrderManager): The RapidataOrderManager instance.
                Deprecated: use ``job`` together with ``audience`` instead.
            validation (ValidationSetManager): The ValidationSetManager instance.
            flow (RapidataFlowManager): The RapidataFlowManager instance.
            audience (RapidataAudienceManager): The RapidataAudienceManager instance.
            job (JobManager): The JobManager instance.
            mri (RapidataBenchmarkManager): The RapidataBenchmarkManager instance.
            signals (RapidataSignalManager): The RapidataSignalManager instance for managing
                recurring audience-job schedules (signals) and observing their runs.
            context (ContextManager): The ContextManager instance for shortening
                datapoint contexts against a question.
        """
        tracer.set_session_id(
            uuid.UUID(int=random.Random().getrandbits(128), version=4).hex
        )

        # Fall back to RAPIDATA_CLIENT_ID / RAPIDATA_CLIENT_SECRET /
        # RAPIDATA_ENVIRONMENT when the caller didn't pass them explicitly.
        # Empty env vars are treated as unset so we fall through to the
        # next layer (credential file / browser flow, or the default env).
        if client_id is None:
            client_id = os.environ.get("RAPIDATA_CLIENT_ID") or None
        if client_secret is None:
            client_secret = os.environ.get("RAPIDATA_CLIENT_SECRET") or None
        if token is None and token_file is None:
            token_file = os.environ.get("RAPIDATA_TOKEN_FILE") or None
        if environment is None:
            environment = os.environ.get("RAPIDATA_ENVIRONMENT") or "rapidata.ai"

        self._client_id = client_id
        self._environment = environment

        rapidata_config.logging.environment = environment
        if environment not in _OTLP_COLLECTOR_ENVIRONMENTS:
            rapidata_config.logging.enable_otlp = False

        with tracer.start_as_current_span("RapidataClient.__init__"):
            logger.debug("Checking version")
            self._check_version()

            logger.debug("Initializing OpenAPIService")
            self._openapi_service = OpenAPIService(
                client_id=client_id,
                client_secret=client_secret,
                environment=environment,
                oauth_scope=oauth_scope,
                cert_path=cert_path,
                token=token,
                token_file=token_file,
                leeway=leeway,
            )

            self._asset_uploader = AssetUploader(openapi_service=self._openapi_service)

            logger.debug("Initializing RapidataOrderManager")
            self.order = RapidataOrderManager(openapi_service=self._openapi_service)

            logger.debug("Initializing ValidationSetManager")
            self.validation = ValidationSetManager(
                openapi_service=self._openapi_service
            )

            logger.debug("Initializing FlowManager")
            self.flow = RapidataFlowManager(openapi_service=self._openapi_service)

            logger.debug("Initializing JobManager")
            self.job = RapidataJobManager(openapi_service=self._openapi_service)

            logger.debug("Initializing RapidataBenchmarkManager")
            self.mri = RapidataBenchmarkManager(openapi_service=self._openapi_service)

            logger.debug("Initializing RapidataSignalManager")
            self.signals = RapidataSignalManager(openapi_service=self._openapi_service)

            logger.debug("Initializing RapidataAudienceManager")
            self.audience = RapidataAudienceManager(
                openapi_service=self._openapi_service
            )

            logger.debug("Initializing RapidataDemographicManager")
            self._demographic = DemographicManager(
                openapi_service=self._openapi_service
            )

            logger.debug("Initializing ContextManager")
            self.context = ContextManager(openapi_service=self._openapi_service)

        self._check_beta_features()  # can't be in the trace for some reason

    def get_token(self) -> dict[str, Any]:
        """Return the complete token object this client authenticates with,
        refreshing it first if it has expired.

        The returned dict has the shape expected by the ``token`` and
        ``token_file`` constructor arguments (``access_token``, ``token_type``
        and an absolute ``expires_at`` timestamp), so it can be written to a
        shared token file that other workers consume — see the Distributed
        Training guide.
        """
        return self._openapi_service.api_client.rest_client.get_token()

    def maintain_token_file(self, path: str, interval: float = 60) -> threading.Thread:
        """Continuously write this client's token to ``path`` so that other
        workers can authenticate from it via ``token_file`` — see the
        Distributed Training guide.

        Writes the file once immediately (creating the parent directory if
        needed), then keeps rewriting it from a background daemon thread every
        ``interval`` seconds. Writes are atomic, and a new token is only
        fetched from the auth server shortly before the current one expires
        (controlled by the client's ``leeway``).

        The file contains a bearer token — write it only to storage that the
        consuming workers alone can read.

        Args:
            path (str): Where to write the token file.
            interval (float, optional): Seconds between rewrites. Defaults to 60.

        Returns:
            threading.Thread: The daemon thread keeping the file fresh. Call
                ``.join()`` on it to block the calling process forever.
        """
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)

        def write_once():
            tmp_path = f"{path}.tmp.{os.getpid()}"
            with open(tmp_path, "w") as f:
                json.dump(self.get_token(), f)
            os.replace(tmp_path, path)

        # First write happens synchronously so the file is guaranteed to
        # exist (or a failure is raised here) before workers are started.
        write_once()

        def loop():
            while True:
                time.sleep(interval)
                try:
                    write_once()
                except Exception as e:
                    logger.warning("Failed to refresh token file %s: %s", path, e)

        thread = threading.Thread(target=loop, daemon=True, name="rapidata-token-file")
        thread.start()
        return thread

    def reset_credentials(self):
        """Reset the credentials saved in the configuration file for the current environment."""
        logger.info("Resetting credentials")
        self._openapi_service.reset_credentials()
        if self._client_id is not None:
            with _userinfo_cache_lock:
                _userinfo_cache.pop((self._environment, self._client_id), None)
        logger.info("Credentials reset")

    def clear_all_caches(self):
        """Clear all caches for the client."""
        self._asset_uploader.clear_cache()
        with _userinfo_cache_lock:
            _userinfo_cache.clear()
        logger.info("All caches cleared")

    def _apply_userinfo(self, result: dict[str, Any]) -> None:
        sub = result.get("sub")
        email = result.get("email")
        if sub and email:
            tracer.set_user_info(client_id=sub, email=email)

        # OIDC userinfo returns `role` as a list when there are
        # multiple, or a bare string when there is exactly one.
        # A substring check like `"Admin" in result.get("role", [])`
        # matches `"Administrator"`, `"SuperAdmin"`, etc., so do an
        # explicit equality check against a normalized list.
        roles_raw = result.get("role", [])
        if isinstance(roles_raw, str):
            roles = [roles_raw]
        elif isinstance(roles_raw, list):
            roles = roles_raw
        else:
            roles = []

        if "Admin" not in roles:
            logger.debug("User is not an admin, not enabling beta features")
            return

        logger.debug("User is an admin, enabling beta features")
        rapidata_config.enableBetaFeatures = True

    def _check_beta_features(self):
        """Enable beta features for the client."""
        with optional_api_call("check beta features"):
            with tracer.start_as_current_span("RapidataClient.check_beta_features"):
                cache_key: tuple[str, str] | None = (
                    (self._environment, self._client_id)
                    if self._client_id is not None
                    else None
                )
                if cache_key is not None:
                    with _userinfo_cache_lock:
                        entry = _userinfo_cache.get(cache_key)
                        if entry is not None and entry.expires_at > time.monotonic():
                            cached_result = entry.result
                        else:
                            cached_result = None
                    if cached_result is not None:
                        logger.debug("Userinfo cache hit for %s", cache_key)
                        self._apply_userinfo(cached_result)
                        return

                result: dict[str, Any] = json.loads(
                    self._openapi_service.api_client.call_api(
                        "GET",
                        f"https://auth.{self._openapi_service.environment}/connect/userinfo",
                        _request_timeout=1,
                    )
                    .read()
                    .decode("utf-8")
                )
                logger.debug("Userinfo: %s", result)

                effective_key = cache_key
                if effective_key is None:
                    sub = result.get("sub")
                    if sub:
                        effective_key = (self._environment, sub)
                if effective_key is not None:
                    with _userinfo_cache_lock:
                        _userinfo_cache[effective_key] = _UserInfoCacheEntry(
                            result=result,
                            expires_at=time.monotonic() + _USERINFO_CACHE_TTL_SECONDS,
                        )

                self._apply_userinfo(result)

    def _check_version(self):
        with optional_api_call("version check"):
            response = requests.get(
                "https://api.github.com/repos/RapidataAI/rapidata-python-sdk/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=1,
            )
            if response.status_code == 200:
                latest_version = response.json()["tag_name"].lstrip("v")
                if version.parse(latest_version) > version.parse(__version__):
                    mark_sdk_outdated(
                        current_version=__version__,
                        latest_version=latest_version,
                    )
                    managed_print(
                        f"""A new version of the Rapidata SDK is available: {latest_version}
Your current version is: {__version__}"""
                    )
                else:
                    logger.debug(
                        "Current version is up to date. Version: %s", __version__
                    )

    def __str__(self) -> str:
        return f"RapidataClient(environment={self._openapi_service.environment})"

    def __repr__(self) -> str:
        return self.__str__()
