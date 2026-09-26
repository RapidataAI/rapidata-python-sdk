"""Point a coding agent at the maintained SDK guide when it imports ``rapidata``.

Agents explore a freshly installed SDK with ``import rapidata`` / ``dir()`` /
``inspect`` before they write a script, and they read stderr but not
docstrings, so the pointer is printed at import time:

- Once per agent session until that session reads the guide with
  ``python -m rapidata skill``. Sessions are told apart by the id the runtime
  exports (:data:`_SESSION_ENV_VARS`); runtimes without one get a read that
  expires after :data:`ANON_READ_TTL`.
- Never while a copy of the skill the agent loads on its own is installed
  (project, user level or the Claude Code plugin), unless a copy written by
  ``--install`` no longer matches the live skill. That is checked at most once
  per :data:`FRESHNESS_TTL` with a :data:`FRESHNESS_TIMEOUT` request, and then
  the pointer asks for a reinstall instead.

``RAPIDATA_AGENT_HINT=0`` switches it off for processes an agent merely started.
State lives in :data:`STATE_FILE`, falling back to the temp dir when a sandbox
makes the home directory read-only. Kept free of SDK imports:
``rapidata/__init__.py`` calls it before loading the client.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SKILL_RAW_URL = "https://raw.githubusercontent.com/RapidataAI/skills/main/plugins/rapidata-sdk-plugin/skills/rapidata/SKILL.md"
LLMS_FULL_URL = "https://docs.rapidata.ai/llms-full.txt"
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
FRESHNESS_TTL = 24 * 3600
FRESHNESS_TIMEOUT = 1.0
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

_STAMP_RE = re.compile(r"<!-- rapidata-skill sha256=([0-9a-f]{64}) fetched=(\S+) -->\n")

AGENT_HINT = (
    "rapidata: coding agent detected. Read the maintained SDK guide before exploring "
    "the installed source (skip if this session already read it):\n"
    "  python -m rapidata skill            # print the guide\n"
    "  python -m rapidata skill --install  # keep it in this project\n"
    f"  {LLMS_FULL_URL}"
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


def skill_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def stamp_skill(content: str, now: datetime | None = None) -> str:
    """Return ``content`` with a provenance line after its front matter, so staleness can be checked later."""
    fetched = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = (
        f"<!-- rapidata-skill sha256={skill_digest(content)} fetched={fetched} -->\n"
    )
    if content.startswith("---\n"):
        end = content.find("\n---\n", 4)
        if end != -1:
            cut = end + len("\n---\n")
            return content[:cut] + stamp + content[cut:]
    return stamp + content


def _installed_digest(text: str) -> str | None:
    """Digest of the live skill this installed copy was made from, or None when it is not the Rapidata skill."""
    match = _STAMP_RE.search(text)
    if match:
        return match.group(1)
    # Copies written by --install before stamping existed are verbatim.
    if text.startswith("---\nname: rapidata\n"):
        return skill_digest(text)
    return None


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


def record_live_skill(content: str) -> None:
    """Remember the live skill's digest so the next freshness check can skip the network."""
    state = _load_state()
    state["live_sha"] = skill_digest(content)
    state["live_checked_at"] = time.time()
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
    """Return ``(agent, install_root, path, digest)`` for each Rapidata skill file in the project ``root`` or the home directory."""
    root = root or Path.cwd()
    candidates = [(a, root, rel) for a, rel in SKILL_INSTALL_PATHS.items()]
    candidates += [(a, Path.home(), rel) for a, rel in USER_SKILL_PATHS.items()]
    copies = []
    for agent, base, rel in candidates:
        path = base / rel
        try:
            digest = _installed_digest(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if digest:
            copies.append((agent, base, path, digest))
    return copies


def _fetch_live_digest() -> str | None:
    try:
        with urllib.request.urlopen(SKILL_RAW_URL, timeout=FRESHNESS_TIMEOUT) as resp:
            return skill_digest(resp.read().decode("utf-8"))
    except Exception:
        return None


def _live_digest(state: dict) -> str | None:
    if time.time() - state.get("live_checked_at", 0) < FRESHNESS_TTL:
        return state.get("live_sha")
    live = _fetch_live_digest()
    # Recorded on failure too, so an offline machine pays the timeout once a day, not per import.
    state["live_checked_at"] = time.time()
    if live:
        state["live_sha"] = live
    _save_state(state)
    return state.get("live_sha")


def _stale_hint(agent: str, base: Path, path: Path) -> str:
    cmd = "python -m rapidata skill --install"
    if agent != "claude":
        cmd += f" --agent {agent}"
    if base != Path.cwd():
        cmd += f" --dir {base}"
    return f"rapidata: the installed Rapidata skill at {path} is outdated. Update it with: {cmd}"


def _running_the_cli() -> bool:
    argv = getattr(sys, "orig_argv", [])
    return any(
        a == "-m" and i + 1 < len(argv) and argv[i + 1] == "rapidata"
        for i, a in enumerate(argv)
    )


def agent_hint() -> str | None:
    """Return the pointer an agent should see on import, or None when it has what it needs."""
    try:
        if not running_under_coding_agent() or _running_the_cli():
            return None
        state = _load_state()
        copies = installed_copies()
        if copies:
            live = _live_digest(state)
            for agent, base, path, digest in copies:
                if live and digest != live:
                    return _stale_hint(agent, base, path)
            return None
        if _plugin_installed() or _read_this_session(state):
            return None
        return AGENT_HINT
    except Exception:
        return None


def print_agent_hint() -> None:
    hint = agent_hint()
    if hint:
        print(hint, file=sys.stderr)
