"""Pytest configuration shared by the whole test suite.

The SDK ships OTLP tracing on by default, and `rapidata_config` reads
`RAPIDATA_DISABLE_OTLP` once at import time. Without this, every test run
exports spans to the production collector: the suite drives the SDK with
`MagicMock` arguments, so the resulting validation failures land in prod
telemetry as real errors from `Rapidata.Python.SDK` and drown out genuine
customer failures.

Setting the env var before `rapidata` is imported is what actually disables
tracing; the explicit config assignment below is a safety net in case something
imported the package during collection first.
"""

import os
import sys
from pathlib import Path

os.environ["RAPIDATA_DISABLE_OTLP"] = "1"

from rapidata.rapidata_client.config import rapidata_config  # noqa: E402

rapidata_config.logging.enable_otlp = False


import pytest  # noqa: E402

from rapidata import _agent_hint  # noqa: E402

_AGENT_VARS = (
    *_agent_hint._AGENT_ENV_VARS,
    *_agent_hint._SESSION_ENV_VARS,
    "RAPIDATA_AGENT_HINT",
    "CLAUDE_CONFIG_DIR",
)


@pytest.fixture
def agent_sandbox(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """An empty home and project with no agent env, no hint state and no network."""
    for var in _AGENT_VARS:
        monkeypatch.delenv(var, raising=False)
    home, project = tmp_path / "home", tmp_path / "project"
    home.mkdir()
    project.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(project)
    monkeypatch.setattr(
        _agent_hint, "STATE_FILE", home / ".config/rapidata/agent-state.json"
    )
    monkeypatch.setattr(_agent_hint, "FALLBACK_STATE_FILE", tmp_path / "tmp-state.json")
    monkeypatch.setattr(_agent_hint, "_fetch_live_digest", lambda: None)
    monkeypatch.setattr(sys, "orig_argv", ["python", "-c", "import rapidata"])
    return project
