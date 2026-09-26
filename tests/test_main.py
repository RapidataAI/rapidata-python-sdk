from __future__ import annotations

from pathlib import Path

import pytest
import requests

from rapidata import __main__ as cli
from rapidata import _agent_hint
from rapidata._agent_hint import skill_digest

SKILL = "---\nname: rapidata\n---\nguide"


@pytest.fixture(autouse=True)
def sandbox(agent_sandbox: Path) -> Path:
    return agent_sandbox


@pytest.fixture
def skill(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(cli, "fetch_skill", lambda: SKILL)
    return SKILL


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> str:
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(cli, "fetch_skill", boom)


def test_skill_prints_the_guide(skill: str, capsys: pytest.CaptureFixture[str]):
    assert cli.main(["skill"]) == 0
    assert capsys.readouterr().out.strip() == skill


def test_skill_install_writes_a_stamped_copy_to_the_claude_path(
    skill: str, tmp_path: Path
):
    assert cli.main(["skill", "--install", "--dir", str(tmp_path)]) == 0
    installed = (tmp_path / ".claude/skills/rapidata/SKILL.md").read_text()
    assert installed.startswith("---\nname: rapidata\n---\n")
    assert f"sha256={skill_digest(skill)}" in installed
    assert installed.endswith("guide")


def test_skill_install_honours_agent(skill: str, tmp_path: Path):
    assert (
        cli.main(["skill", "--install", "--agent", "generic", "--dir", str(tmp_path)])
        == 0
    )
    assert (tmp_path / "AGENTS.md").read_text().endswith("guide")


def test_offline_falls_back_to_the_bundled_copy(
    offline: None, capsys: pytest.CaptureFixture[str]
):
    assert cli.main(["skill"]) == 0
    out = capsys.readouterr()
    assert out.out.startswith("---\nname: rapidata\n")
    assert "bundled" in out.err


def test_offline_without_a_bundled_copy_points_at_the_online_copy(
    offline: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr(cli, "bundled_skill", lambda: None)
    assert cli.main(["skill"]) == 1
    assert "llms-full.txt" in capsys.readouterr().err


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]):
    assert cli.main([]) == 0
    assert "skill" in capsys.readouterr().out


def test_reading_the_skill_marks_this_session(
    skill: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    assert _agent_hint.agent_hint() is not None
    assert cli.main(["skill"]) == 0
    assert _agent_hint.agent_hint() is None


def test_reading_the_skill_records_the_live_digest(skill: str):
    assert cli.main(["skill"]) == 0
    assert _agent_hint._load_state()["live_sha"] == skill_digest(skill)
