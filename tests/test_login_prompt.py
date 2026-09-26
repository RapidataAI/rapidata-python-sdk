from __future__ import annotations

from pathlib import Path

import pytest

from rapidata import _agent_hint
from rapidata.rapidata_client.config import rapidata_config
from rapidata.service.credential_manager import CredentialManager


@pytest.fixture
def manager(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CredentialManager:
    for var in _agent_hint._AGENT_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return CredentialManager(endpoint="https://auth.rapidata.ai")


def test_prints_the_url_even_when_the_browser_opened(
    manager: CredentialManager, capsys: pytest.CaptureFixture[str]
):
    manager._print_login_prompt("https://auth.rapidata.ai/login?x=1", True)
    err = capsys.readouterr().err
    assert "https://auth.rapidata.ai/login?x=1" in err
    assert "Coding agent" not in err


def test_tells_a_coding_agent_to_relay_the_url(
    manager: CredentialManager,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setattr(rapidata_config.logging, "silent_mode", True)
    manager._print_login_prompt("https://auth.rapidata.ai/login", False)
    err = capsys.readouterr().err
    assert "https://auth.rapidata.ai/login" in err
    assert "show this URL to the user" in err
