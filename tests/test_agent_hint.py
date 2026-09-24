from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from rapidata import _agent_hint
from rapidata._agent_hint import (
    AGENT_HINT,
    agent_hint,
    mark_skill_read,
    running_under_coding_agent,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    for var in _agent_hint._AGENT_ENV_VARS + ("RAPIDATA_AGENT_HINT",):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(_agent_hint, "SKILL_READ_MARKER", tmp_path / "skill-read")
    monkeypatch.setattr(sys, "orig_argv", ["python", "-c", "import rapidata"])


def test_not_detected_in_a_plain_shell():
    assert running_under_coding_agent() is False
    assert agent_hint() is None


@pytest.mark.parametrize("var", _agent_hint._AGENT_ENV_VARS)
def test_detected_by_agent_env_var(monkeypatch: pytest.MonkeyPatch, var: str):
    monkeypatch.setenv(var, "1")
    assert agent_hint() == AGENT_HINT


@pytest.mark.parametrize("value", ["0", "false", "NO"])
def test_override_silences(monkeypatch: pytest.MonkeyPatch, value: str):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("RAPIDATA_AGENT_HINT", value)
    assert agent_hint() is None


def test_silent_once_the_guide_was_read(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    mark_skill_read()
    assert agent_hint() is None


def test_silent_when_the_skill_is_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("CLAUDECODE", "1")
    target = tmp_path / _agent_hint.SKILL_INSTALL_PATHS["claude"]
    target.parent.mkdir(parents=True)
    target.write_text("guide")
    assert agent_hint() is None


def test_silent_while_running_the_skill_cli(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setattr(sys, "orig_argv", ["python", "-m", "rapidata", "skill"])
    assert agent_hint() is None


def test_import_prints_the_hint_to_stderr(tmp_path: Path):
    env = {k: v for k, v in os.environ.items() if k not in _agent_hint._AGENT_ENV_VARS}
    env.update(CLAUDECODE="1", HOME=str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-c", "import rapidata"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "python -m rapidata skill" in result.stderr
    assert result.stdout == ""
