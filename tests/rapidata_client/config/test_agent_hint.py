from __future__ import annotations

from pathlib import Path

import pytest

from rapidata.rapidata_client.config import _agent_hint
from rapidata.rapidata_client.config._agent_hint import (
    AGENT_HINT,
    agent_hint_once,
    running_under_coding_agent,
    skill_installed,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    for var in _agent_hint._AGENT_ENV_VARS + ("RAPIDATA_AGENT_HINT",):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_agent_hint, "_hint_shown", False)


def test_not_detected_in_a_plain_shell():
    assert running_under_coding_agent() is False
    assert agent_hint_once() is None


@pytest.mark.parametrize("var", _agent_hint._AGENT_ENV_VARS)
def test_detected_by_agent_env_var(monkeypatch: pytest.MonkeyPatch, var: str):
    monkeypatch.setenv(var, "1")
    assert running_under_coding_agent() is True


@pytest.mark.parametrize("value", ["0", "false", "NO"])
def test_override_silences(monkeypatch: pytest.MonkeyPatch, value: str):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("RAPIDATA_AGENT_HINT", value)
    assert running_under_coding_agent() is False


def test_override_forces(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAPIDATA_AGENT_HINT", "1")
    assert running_under_coding_agent() is True


def test_hint_shown_once_per_process(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert agent_hint_once() == AGENT_HINT
    assert agent_hint_once() is None


def test_hint_suppressed_when_skill_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("CLAUDECODE", "1")
    target = tmp_path / ".claude/skills/rapidata/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("skill")
    assert skill_installed() is True
    assert agent_hint_once() is None
