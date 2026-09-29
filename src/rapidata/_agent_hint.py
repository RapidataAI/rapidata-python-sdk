"""Point a coding agent at the guide bundled with this SDK when it imports ``rapidata``.

Agents explore a freshly installed SDK with ``import rapidata`` / ``dir()`` /
``inspect`` before they write a script, and they read stderr but not
docstrings, so the pointer is printed at import time:

- Once per agent session until that session reads the guide with
  ``python -m rapidata skill``. Sessions are told apart by the id the runtime
  exports (:data:`_SESSION_ENV_VARS`); runtimes without one get a read that
  expires after :data:`ANON_READ_TTL`.
- Never while a copy written by ``python -m rapidata skill --install``
  (project or user level) carries this SDK's version in its front matter. A
  copy from another version asks for a reinstall instead. Nothing here touches
  the network.

``RAPIDATA_AGENT_HINT=0`` switches it off for processes an agent merely started.
State lives in :data:`STATE_FILE`, falling back to the temp dir when a sandbox
makes the home directory read-only. Kept free of client imports:
``rapidata/__init__.py`` calls it before loading the client.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

AGENT_DOCS_URL = "https://docs.rapidata.ai/ai_agents/"

# Where each agent picks up a project-local skill file, relative to the project root.
SKILL_INSTALL_PATHS: dict[str, str] = {
    "claude": ".claude/skills/rapidata/SKILL.md",
    "cursor": ".cursor/rules/rapidata.mdc",
    "codex": ".codex/skills/rapidata/SKILL.md",
    "generic": "AGENTS.md",
}

# User-level skill files the runtimes load in every project, relative to the home directory.
USER_SKILL_PATHS: dict[str, str] = {
    "claude": ".claude/skills/rapidata/SKILL.md",
    "codex": ".codex/skills/rapidata/SKILL.md",
}

STATE_FILE = Path.home() / ".config" / "rapidata" / "agent-state.json"
FALLBACK_STATE_FILE = Path(tempfile.gettempdir()) / "rapidata-agent-state.json"

ANON_READ_TTL = 12 * 3600
_PRUNE_AFTER = 7 * 24 * 3600

# Env var each agent runtime exports -> the name reported in traces. Specific
# vars come before the generic AI_AGENT so the first match names the runtime.
_AGENT_ENV_VARS: dict[str, str] = {
    "CLAUDECODE": "claude-code",
    "CURSOR_AGENT": "cursor",
    "CODEX_THREAD_ID": "codex",
    "CODEX_SANDBOX": "codex",
    "GEMINI_CLI": "gemini-cli",
    "AI_AGENT": "unknown",
}

_SESSION_ENV_VARS = ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID", "CODEX_SESSION_ID")

_STAMP_RE = re.compile(r'^  rapidata-sdk-version: "([^"]+)"$', re.MULTILINE)

AGENT_HINT = (
    "rapidata: coding agent detected. Read the SDK guide for this version before exploring "
    "the installed source (skip if this session already read it):\n"
    "  python -m rapidata skill            # print the guide\n"
    "  python -m rapidata skill --install  # keep it in this project\n"
    "Before the first RapidataClient(), run `python -m rapidata status`. If it reports not logged in,\n"
    "run `python -m rapidata login` and show the user the URL it prints (it waits up to 5 minutes)."
)


def detected_coding_agent() -> str | None:
    """Return the name of the coding-agent runtime driving this process, or None.

    Ignores ``RAPIDATA_AGENT_HINT``: silencing the hint does not change what drives the process.
    """
    return next(
        (name for var, name in _AGENT_ENV_VARS.items() if os.environ.get(var)), None
    )


def running_under_coding_agent() -> bool:
    """Return True when a known coding-agent runtime drives this process and the hint is not switched off."""
    if os.environ.get("RAPIDATA_AGENT_HINT", "").lower() in ("0", "false", "no"):
        return False
    return detected_coding_agent() is not None


def _sdk_version() -> str:
    # Lazy: rapidata/__init__.py imports this module while the package is still loading.
    from rapidata import __version__

    return __version__


def _install_command(agent: str, directory: str | None = None) -> str:
    cmd = "python -m rapidata skill --install"
    if agent != "claude":
        cmd += f" --agent {agent}"
    if directory:
        cmd += f" --dir {directory}"
    return cmd


def stamp_skill(
    content: str,
    agent: str = "claude",
    user_level: bool = False,
    version: str | None = None,
) -> str:
    """Return ``content`` with the SDK version in its front matter and a version check as its first lines.

    The front matter field is what :func:`installed_version` reads on import;
    the check lets an agent that loads the copy without importing the SDK
    notice that it drifted from the installed version.
    """
    version = version or _sdk_version()
    where = "" if user_level else " from the project root"
    cmd = _install_command(agent, "~" if user_level else None)
    check = (
        f"> **Installed copy, written by rapidata {version}.** Before relying on it, run\n"
        f'> `python -c "import rapidata; print(rapidata.__version__)"`. If that does not print\n'
        f"> `{version}`, run `{cmd}`{where} to update this file, then read it again.\n"
    )
    field = f'metadata:\n  rapidata-sdk-version: "{version}"\n'
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            cut = end + len("\n---\n")
            return content[: end + 1] + field + "---\n" + check + content[cut:]
    return f"---\n{field}---\n{check}{content}"


def installed_version(text: str) -> str | None:
    """SDK version an ``--install``ed copy was written by, or None when its front matter carries no stamp."""
    end = text.find("\n---\n", 4) if text.startswith("---\n") else -1
    match = _STAMP_RE.search(text[:end]) if end != -1 else None
    return match.group(1) if match else None


def _load_state() -> dict:
    state: dict = {"reads": {}}
    for path in (FALLBACK_STATE_FILE, STATE_FILE):
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(loaded, dict):
            reads = {**state["reads"], **loaded.get("reads", {})}
            state.update(loaded)
            state["reads"] = reads
    return state


def _save_state(state: dict) -> None:
    now = time.time()
    state["reads"] = {
        k: t for k, t in state.get("reads", {}).items() if now - t < _PRUNE_AFTER
    }
    payload = json.dumps(state)
    for path in (STATE_FILE, FALLBACK_STATE_FILE):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
            return
        except OSError:
            continue


def _session_key() -> str | None:
    return next(
        (
            f"{var}:{os.environ[var]}"
            for var in _SESSION_ENV_VARS
            if os.environ.get(var)
        ),
        None,
    )


def _read_this_session(state: dict) -> bool:
    reads = state.get("reads", {})
    key = _session_key()
    if key:
        return key in reads
    read_at = reads.get("anonymous")
    return read_at is not None and time.time() - read_at < ANON_READ_TTL


def mark_skill_read() -> None:
    state = _load_state()
    state["reads"][_session_key() or "anonymous"] = time.time()
    _save_state(state)


def installed_copies(root: Path | None = None) -> list[tuple[str, Path, Path, str]]:
    """Return ``(agent, install_root, path, version)`` for each stamped skill file in the project ``root`` or the home directory."""
    root = root or Path.cwd()
    candidates = [(a, root, rel) for a, rel in SKILL_INSTALL_PATHS.items()]
    candidates += [(a, Path.home(), rel) for a, rel in USER_SKILL_PATHS.items()]
    copies = []
    for agent, base, rel in candidates:
        path = base / rel
        try:
            version = installed_version(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if version:
            copies.append((agent, base, path, version))
    return copies


def _stale_hint(agent: str, base: Path, path: Path, version: str) -> str:
    cmd = _install_command(agent, None if base == Path.cwd() else str(base))
    return (
        f"rapidata: the Rapidata skill at {path} was installed by rapidata {version}, "
        f"but {_sdk_version()} is installed. Update it with: {cmd}"
    )


def _running_the_cli() -> bool:
    argv = getattr(sys, "orig_argv", [])
    if any(
        a == "-m" and i + 1 < len(argv) and argv[i + 1] == "rapidata"
        for i, a in enumerate(argv)
    ):
        return True
    # The `rapidata` console script imports the package before main() runs.
    return bool(sys.argv) and Path(sys.argv[0]).stem == "rapidata"


def agent_hint() -> str | None:
    """Return the pointer an agent should see on import, or None when it has what it needs."""
    try:
        if not running_under_coding_agent() or _running_the_cli():
            return None
        copies = installed_copies()
        current = _sdk_version()
        for agent, base, path, version in copies:
            if version != current:
                return _stale_hint(agent, base, path, version)
        if copies or _read_this_session(_load_state()):
            return None
        return AGENT_HINT
    except Exception:
        return None


def print_agent_hint() -> None:
    hint = agent_hint()
    if hint:
        print(hint, file=sys.stderr)
