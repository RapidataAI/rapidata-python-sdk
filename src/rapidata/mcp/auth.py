"""Client-resolution seam for the Rapidata MCP server.

Tools never construct a :class:`RapidataClient` themselves; they ask a
``ClientProvider`` for one. This is the boundary that lets the same tool code
run under different auth models:

* ``EnvClientProvider`` — ambient credentials from the SDK's own resolution
  chain (``RAPIDATA_CLIENT_ID`` / ``RAPIDATA_CLIENT_SECRET`` env vars, then the
  on-disk credential file). One stdio server process serves exactly one
  customer, so the client is built once and reused.
* ``TokenClientProvider`` — a pre-obtained OAuth token. This is the entry point
  a hosted, multi-tenant transport plugs into: validate the caller's bearer
  token, then build a per-request client scoped to that customer. The SDK
  already accepts a ``token`` object, so no SDK change is needed to get here.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from rapidata import RapidataClient


class ClientProvider(Protocol):
    """Resolves an authenticated :class:`RapidataClient` for a tool call."""

    def get_client(self) -> RapidataClient: ...


class EnvClientProvider:
    """Builds one :class:`RapidataClient` from ambient credentials and reuses it."""

    def __init__(self) -> None:
        self._client: RapidataClient | None = None
        self._lock = threading.Lock()

    def get_client(self) -> RapidataClient:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from rapidata import RapidataClient

                    self._client = RapidataClient()
        return self._client


class TokenClientProvider:
    """Builds a :class:`RapidataClient` from a caller-supplied OAuth token.

    The token must be the complete object the SDK expects (access token, token
    type, expiry) — the same shape returned by the OAuth token endpoint.
    """

    def __init__(self, token: dict, environment: str | None = None) -> None:
        self._token = token
        self._environment = environment

    def get_client(self) -> RapidataClient:
        from rapidata import RapidataClient

        return RapidataClient(token=self._token, environment=self._environment)
