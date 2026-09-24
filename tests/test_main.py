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
