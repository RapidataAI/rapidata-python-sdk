from __future__ import annotations

import os
from pathlib import Path

import pytest

from rapidata import __main__ as cli
from rapidata import __version__, _agent_hint


@pytest.fixture(autouse=True)
def sandbox(agent_sandbox: Path) -> Path:
    return agent_sandbox


def test_skill_prints_the_bundled_guide(capsys: pytest.CaptureFixture[str]):
    assert cli.main(["skill"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("---\nname: rapidata\n")
    assert "python -m rapidata skill reference" in out


@pytest.mark.parametrize(
    "guide", ["reference", "examples", "flows-for-preference-data"]
)
def test_skill_prints_each_companion_guide(
    guide: str, capsys: pytest.CaptureFixture[str]
):
    assert cli.main(["skill", guide]) == 0
    assert capsys.readouterr().out.startswith("# ")


def test_skill_does_not_touch_the_network(monkeypatch: pytest.MonkeyPatch):
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError("`rapidata skill` must not touch the network")

    monkeypatch.setattr(socket, "create_connection", no_network)
    assert cli.main(["skill"]) == 0


def test_skill_survives_a_closed_pipe(tmp_path: Path):
    import subprocess
    import sys

    result = subprocess.run(
        f'"{sys.executable}" -m rapidata skill | head -1',
        shell=True,
        cwd=tmp_path,
        env={**os.environ, "HOME": str(tmp_path), "RAPIDATA_AGENT_HINT": "0"},
        capture_output=True,
        text=True,
    )
    assert result.stdout == "---\n"
    assert "BrokenPipeError" not in result.stderr


def test_skill_install_writes_a_version_stamped_copy_to_the_claude_path(
    tmp_path: Path,
):
    assert cli.main(["skill", "--install", "--dir", str(tmp_path)]) == 0
    installed = (tmp_path / ".claude/skills/rapidata/SKILL.md").read_text()
    assert installed.startswith("---\nname: rapidata\n")
    assert _agent_hint.installed_version(installed) == __version__
    assert installed.endswith(cli.bundled_skill().split("\n---\n", 1)[1])


def test_skill_install_honours_agent(tmp_path: Path):
    assert (
        cli.main(["skill", "--install", "--agent", "generic", "--dir", str(tmp_path)])
        == 0
    )
    assert _agent_hint.installed_version((tmp_path / "AGENTS.md").read_text()) == (
        __version__
    )


def test_install_rejects_a_companion_guide(tmp_path: Path):
    with pytest.raises(SystemExit):
        cli.main(["skill", "reference", "--install", "--dir", str(tmp_path)])


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]):
    assert cli.main([]) == 0
    assert "skill" in capsys.readouterr().out


def test_reading_the_skill_marks_this_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    assert _agent_hint.agent_hint() is not None
    assert cli.main(["skill"]) == 0
    assert _agent_hint.agent_hint() is None


def test_reading_a_companion_guide_does_not_mark_the_session(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    assert cli.main(["skill", "examples"]) == 0
    assert _agent_hint.agent_hint() is not None


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
