from __future__ import annotations

from pathlib import Path

import pytest
import requests

from rapidata import __main__ as cli
from rapidata import _agent_hint


@pytest.fixture(autouse=True)
def marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "skill-read"
    monkeypatch.setattr(_agent_hint, "SKILL_READ_MARKER", path)
    return path


@pytest.fixture
def skill(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(cli, "fetch_skill", lambda: "---\nname: rapidata\n---\nguide")
    return "---\nname: rapidata\n---\nguide"


def test_skill_prints_the_guide(skill: str, capsys: pytest.CaptureFixture[str]):
    assert cli.main(["skill"]) == 0
    assert capsys.readouterr().out.strip() == skill


def test_skill_install_writes_claude_path_by_default(skill: str, tmp_path: Path):
    assert cli.main(["skill", "--install", "--dir", str(tmp_path)]) == 0
    assert (tmp_path / ".claude/skills/rapidata/SKILL.md").read_text() == skill


def test_skill_install_honours_agent(skill: str, tmp_path: Path):
    assert (
        cli.main(["skill", "--install", "--agent", "generic", "--dir", str(tmp_path)])
        == 0
    )
    assert (tmp_path / "AGENTS.md").read_text() == skill


def test_fetch_failure_points_at_the_online_copy(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    def boom() -> str:
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(cli, "fetch_skill", boom)
    assert cli.main(["skill"]) == 1
    assert "llms-full.txt" in capsys.readouterr().err


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]):
    assert cli.main([]) == 0
    assert "skill" in capsys.readouterr().out


def test_reading_the_skill_writes_the_marker(skill: str, marker: Path):
    assert cli.main(["skill"]) == 0
    assert marker.is_file()


@pytest.fixture
def no_auth_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    for var in (
        "RAPIDATA_TOKEN_FILE",
        "RAPIDATA_CLIENT_ID",
        "RAPIDATA_CLIENT_SECRET",
        "RAPIDATA_ENVIRONMENT",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


def test_status_without_credentials_points_at_login(
    no_auth_env, capsys: pytest.CaptureFixture[str]
):
    assert cli.main(["status"]) == 1
    assert "python -m rapidata login" in capsys.readouterr().out


def test_status_accepts_env_credentials(
    no_auth_env, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setenv("RAPIDATA_CLIENT_ID", "id")
    monkeypatch.setenv("RAPIDATA_CLIENT_SECRET", "secret")
    assert cli.main(["status"]) == 0
    assert "RAPIDATA_CLIENT_ID" in capsys.readouterr().out


def test_login_runs_the_browser_flow_when_not_authenticated(
    no_auth_env, monkeypatch: pytest.MonkeyPatch
):
    from rapidata.service.credential_manager import CredentialManager

    calls: list[str] = []

    def fake_login(self: CredentialManager):
        calls.append(self.endpoint)
        return object()

    monkeypatch.setattr(CredentialManager, "get_client_credentials", fake_login)
    assert cli.main(["login", "--environment", "rapidata.ai"]) == 0
    assert calls == ["https://auth.rapidata.ai"]
