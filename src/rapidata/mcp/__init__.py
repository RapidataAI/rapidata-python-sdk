"""Rapidata MCP server — expose Rapidata labeling tasks to MCP-capable agents.

This is an optional integration. Install it with ``pip install 'rapidata[mcp]'``
and run the ``rapidata-mcp`` console script, or ``python -m rapidata.mcp``.
"""

from __future__ import annotations

from rapidata.mcp.auth import ClientProvider, EnvClientProvider, TokenClientProvider
from rapidata.mcp.server import build_server, main

__all__ = [
    "build_server",
    "main",
    "ClientProvider",
    "EnvClientProvider",
    "TokenClientProvider",
]
