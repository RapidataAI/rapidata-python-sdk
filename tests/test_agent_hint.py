from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from rapidata import __version__, _agent_hint
from rapidata._agent_hint import (
    AGENT_HINT,
    agent_hint,
    detected_coding_agent,
    installed_version,
    mark_skill_read,
    running_under_coding_agent,
    stamp_skill,
)

SKILL = "---\nname: rapidata\ndescription: guide\n---\n# Rapidata\n"


@pytest.fixture(autouse=True)
def sandbox(agent_sandbox: Path) -> Path:
    return agent_sandbox


def _agent(monkeypatch: pytest.MonkeyPatch, session: str | None = "s1") -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    if session:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session)
    else:
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)


def _install(
    base: Path, content: str, rel: str = ".claude/skills/rapidata/SKILL.md"
) -> Path:
    target = base / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return target


def _after(monkeypatch: pytest.MonkeyPatch, seconds: float) -> None:
    later = time.time() + seconds
    monkeypatch.setattr(_agent_hint.time, "time", lambda: later)


def test_not_detected_in_a_plain_shell():
    assert running_under_coding_agent() is False
    assert agent_hint() is None


@pytest.mark.parametrize("var", _agent_hint._AGENT_ENV_VARS)
def test_detected_by_agent_env_var(monkeypatch: pytest.MonkeyPatch, var: str):
    monkeypatch.setenv(var, "1")
    assert agent_hint() == AGENT_HINT


@pytest.mark.parametrize("value", ["0", "false", "NO"])
def test_override_silences(monkeypatch: pytest.MonkeyPatch, value: str):
    _agent(monkeypatch)
    monkeypatch.setenv("RAPIDATA_AGENT_HINT", value)
    assert agent_hint() is None


def test_override_cannot_force_the_hint_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAPIDATA_AGENT_HINT", "1")
    assert agent_hint() is None


def test_hint_does_not_advertise_the_off_switch():
    assert "RAPIDATA_AGENT_HINT" not in AGENT_HINT


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, None),
        ({"CLAUDECODE": "1", "AI_AGENT": "claude-code/2"}, "claude-code"),
        ({"CURSOR_AGENT": "1"}, "cursor"),
        ({"CODEX_SANDBOX": "seatbelt"}, "codex"),
        ({"AI_AGENT": "something-new"}, "unknown"),
    ],
)
def test_detected_coding_agent_names_the_runtime(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str], expected: str | None
):
    for var, value in env.items():
        monkeypatch.setenv(var, value)
    assert detected_coding_agent() == expected


def test_detection_ignores_hint_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("RAPIDATA_AGENT_HINT", "0")
    assert detected_coding_agent() == "claude-code"
    assert running_under_coding_agent() is False


def test_silent_once_this_session_read_the_guide(monkeypatch: pytest.MonkeyPatch):
    _agent(monkeypatch, "s1")
    mark_skill_read()
    assert agent_hint() is None


def test_a_new_session_on_the_same_machine_is_hinted_again(
    monkeypatch: pytest.MonkeyPatch,
):
    _agent(monkeypatch, "s1")
    mark_skill_read()
    _agent(monkeypatch, "s2")
    assert agent_hint() == AGENT_HINT


def test_codex_sessions_are_keyed_by_thread_id(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CODEX_THREAD_ID", "t1")
    mark_skill_read()
    assert agent_hint() is None
    monkeypatch.setenv("CODEX_THREAD_ID", "t2")
    assert agent_hint() == AGENT_HINT


def test_read_without_a_session_id_expires(monkeypatch: pytest.MonkeyPatch):
    _agent(monkeypatch, session=None)
    mark_skill_read()
    assert agent_hint() is None
    _after(monkeypatch, _agent_hint.ANON_READ_TTL + 1)
    assert agent_hint() == AGENT_HINT


def test_read_is_kept_when_home_is_read_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _agent(monkeypatch)
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("")
    monkeypatch.setattr(_agent_hint, "STATE_FILE", blocker / "agent-state.json")
    mark_skill_read()
    assert _agent_hint.FALLBACK_STATE_FILE.is_file()
    assert agent_hint() is None


def test_silent_while_running_the_skill_cli(monkeypatch: pytest.MonkeyPatch):
    _agent(monkeypatch)
    monkeypatch.setattr(sys, "orig_argv", ["python", "-m", "rapidata", "skill"])
    assert agent_hint() is None


def test_silent_when_the_plugin_is_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _agent(monkeypatch)
    config = tmp_path / "claude-config"
    (config / "plugins").mkdir(parents=True)
    (config / "plugins/installed_plugins.json").write_text(
        json.dumps({"plugins": {"rapidata-sdk-plugin@rapidata-sdk-marketplace": []}})
    )
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    assert agent_hint() is None


def test_an_unrelated_agents_md_does_not_count_as_installed(
    monkeypatch: pytest.MonkeyPatch, sandbox: Path
):
    _agent(monkeypatch)
    _install(sandbox, "# Our repo conventions\n", "AGENTS.md")
    assert agent_hint() == AGENT_HINT


@pytest.mark.parametrize("where", ["project", "home"])
def test_silent_when_an_installed_copy_matches_this_version(
    monkeypatch: pytest.MonkeyPatch, sandbox: Path, where: str
):
    _agent(monkeypatch)
    _install(sandbox if where == "project" else Path.home(), stamp_skill(SKILL))
    assert agent_hint() is None


def test_a_copy_from_another_version_asks_for_a_reinstall(
    monkeypatch: pytest.MonkeyPatch, sandbox: Path
):
    _agent(monkeypatch)
    path = _install(sandbox, stamp_skill(SKILL, version="3.0.0"))
    mark_skill_read()
    hint = agent_hint()
    assert hint is not None and str(path) in hint
    assert "3.0.0" in hint and __version__ in hint
    assert hint.endswith("python -m rapidata skill --install")


def test_outdated_user_level_copy_names_its_dir(monkeypatch: pytest.MonkeyPatch):
    _agent(monkeypatch)
    _install(
        Path.home(),
        stamp_skill(SKILL, version="3.0.0"),
        ".codex/skills/rapidata/SKILL.md",
    )
    hint = agent_hint()
    assert hint is not None
    assert hint.endswith(f"--install --agent codex --dir {Path.home()}")


def test_an_unstamped_copy_does_not_count_as_installed(
    monkeypatch: pytest.MonkeyPatch, sandbox: Path
):
    _agent(monkeypatch)
    _install(sandbox, SKILL)
    assert agent_hint() == AGENT_HINT


def test_silent_while_running_the_console_script(monkeypatch: pytest.MonkeyPatch):
    _agent(monkeypatch)
    monkeypatch.setattr(sys, "orig_argv", ["python", "/venv/bin/rapidata", "skill"])
    monkeypatch.setattr(sys, "argv", ["/venv/bin/rapidata", "skill"])
    assert agent_hint() is None


def test_stamp_puts_the_version_in_the_front_matter():
    stamped = stamp_skill(SKILL)
    front_matter, body = stamped.split("---\n")[1:3]
    assert front_matter.startswith("name: rapidata\n")
    assert f'rapidata-sdk-version: "{__version__}"' in front_matter
    assert installed_version(stamped) == __version__
    assert body.startswith(f"> **Installed copy, written by rapidata {__version__}.**")


def test_stamp_tells_the_agent_how_to_update_the_copy():
    body = stamp_skill(SKILL, agent="codex", user_level=True).split("---\n")[2]
    assert "rapidata.__version__" in body
    assert "python -m rapidata skill --install --agent codex --dir ~" in body


def test_a_stamp_in_the_body_is_not_read_as_the_version():
    assert installed_version(SKILL + '  rapidata-sdk-version: "1.0"\n') is None


def test_hint_needs_no_network(monkeypatch: pytest.MonkeyPatch, sandbox: Path):
    import socket

    def no_network(*args, **kwargs):
        raise AssertionError("the import hint must not touch the network")

    monkeypatch.setattr(socket, "create_connection", no_network)
    _agent(monkeypatch)
    _install(sandbox, stamp_skill(SKILL, version="3.0.0"))
    assert agent_hint() is not None


def test_import_prints_the_hint_to_stderr(tmp_path: Path):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in (*_agent_hint._AGENT_ENV_VARS, *_agent_hint._SESSION_ENV_VARS)
    }
    env.update(CLAUDECODE="1", HOME=str(tmp_path), TMPDIR=str(tmp_path))
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
