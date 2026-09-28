"""Point a coding agent at the guide bundled with this SDK when it imports ``rapidata``.

Agents explore a freshly installed SDK with ``import rapidata`` / ``dir()`` /
``inspect`` before they write a script, and they read stderr but not
docstrings, so the pointer is printed at import time:

- Once per agent session until that session reads the guide with
  ``python -m rapidata skill``. Sessions are told apart by the id the runtime
  exports (:data:`_SESSION_ENV_VARS`); runtimes without one get a read that
  expires after :data:`ANON_READ_TTL`.
- Never while the Claude Code plugin is installed, or while a copy written by
  ``python -m rapidata skill --install`` (project or user level) carries this
  SDK's version stamp. A copy stamped with another version asks for a
  reinstall instead. Nothing here touches the network.

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
PLUGIN_NAME = "rapidata-sdk-plugin"

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

_STAMP_RE = re.compile(r"<!-- rapidata-skill version=(\S+) -->\n")

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


def stamp_skill(content: str, version: str | None = None) -> str:
    """Return ``content`` with a version line after its front matter, so a copy made by another SDK version can be told apart."""
    stamp = f"<!-- rapidata-skill version={version or _sdk_version()} -->\n"
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            cut = end + len("\n---\n")
            return content[:cut] + stamp + content[cut:]
    return stamp + content


def installed_version(text: str) -> str | None:
    """SDK version an ``--install``ed copy was written by, or None when ``text`` carries no stamp."""
    match = _STAMP_RE.search(text)
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


def _plugin_installed() -> bool:
    config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    try:
        plugins = json.loads(
            (config_dir / "plugins" / "installed_plugins.json").read_text(
                encoding="utf-8"
            )
        ).get("plugins", {})
    except (OSError, ValueError, AttributeError):
        return False
    return any(name.split("@", 1)[0] == PLUGIN_NAME for name in plugins)


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
    cmd = "python -m rapidata skill --install"
    if agent != "claude":
        cmd += f" --agent {agent}"
    if base != Path.cwd():
        cmd += f" --dir {base}"
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
        if copies or _plugin_installed() or _read_this_session(_load_state()):
            return None
        return AGENT_HINT
    except Exception:
        return None


def print_agent_hint() -> None:
    hint = agent_hint()
    if hint:
        print(hint, file=sys.stderr)
