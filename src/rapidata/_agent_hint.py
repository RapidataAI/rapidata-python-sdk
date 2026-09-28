"""Point a coding agent at the maintained SDK guide the first time it imports ``rapidata``.

Agents explore a freshly installed SDK with ``import rapidata`` / ``dir()`` /
``inspect`` before they write a script, and they read stderr but not
docstrings, so the pointer is printed at import time. It stays silent once the
guide has been read (``python -m rapidata skill`` writes :data:`SKILL_READ_MARKER`)
or installed into the project, and outside a known agent runtime.

Kept free of SDK imports: ``rapidata/__init__.py`` calls it before loading the client.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SKILL_RAW_URL = "https://raw.githubusercontent.com/RapidataAI/skills/main/plugins/rapidata-sdk-plugin/skills/rapidata/SKILL.md"
LLMS_FULL_URL = "https://docs.rapidata.ai/llms-full.txt"
AGENT_DOCS_URL = "https://docs.rapidata.ai/ai_agents/"

# Where each agent picks up a project-local skill file, relative to the project root.
SKILL_INSTALL_PATHS: dict[str, str] = {
    "claude": ".claude/skills/rapidata/SKILL.md",
    "cursor": ".cursor/rules/rapidata.mdc",
    "codex": ".codex/skills/rapidata/SKILL.md",
    "generic": "AGENTS.md",
}

SKILL_READ_MARKER = Path.home() / ".config" / "rapidata" / "skill-read"

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

AGENT_HINT = (
    "rapidata: coding agent detected. Before exploring the installed source, "
    "read the maintained SDK guide (job types, audiences, result fields, common mistakes):\n"
    "  python -m rapidata skill            # print the guide\n"
    "  python -m rapidata skill --install  # keep it in this project\n"
    f"  {LLMS_FULL_URL}\n"
    "Before the first RapidataClient(), run `python -m rapidata status`. If it reports not logged in,\n"
    "run `python -m rapidata login` and show the user the URL it prints (it waits up to 5 minutes).\n"
    "This message stops once the guide has been read. RAPIDATA_AGENT_HINT=0 silences it."
)


def detected_coding_agent() -> str | None:
    """Return the name of the coding-agent runtime driving this process, or None.

    Ignores ``RAPIDATA_AGENT_HINT``: silencing the hint does not change what drives the process.
    """
    return next(
        (name for var, name in _AGENT_ENV_VARS.items() if os.environ.get(var)), None
    )


def running_under_coding_agent() -> bool:
    """Return True when a known coding-agent runtime drives this process.

    ``RAPIDATA_AGENT_HINT`` overrides detection: ``0``/``false``/``no`` never
    hints, ``1``/``true``/``yes`` always hints.
    """
    override = os.environ.get("RAPIDATA_AGENT_HINT", "").lower()
    if override in ("0", "false", "no"):
        return False
    if override in ("1", "true", "yes"):
        return True
    return detected_coding_agent() is not None


def skill_seen(root: Path | None = None) -> bool:
    """Return True when the guide was read on this machine or installed under ``root`` (default: cwd)."""
    if SKILL_READ_MARKER.is_file():
        return True
    root = root or Path.cwd()
    return any((root / rel).is_file() for rel in SKILL_INSTALL_PATHS.values())


def mark_skill_read() -> None:
    try:
        SKILL_READ_MARKER.parent.mkdir(parents=True, exist_ok=True)
        SKILL_READ_MARKER.touch()
    except OSError:
        pass


def _running_the_cli() -> bool:
    argv = getattr(sys, "orig_argv", [])
    return any(
        a == "-m" and i + 1 < len(argv) and argv[i + 1] == "rapidata"
        for i, a in enumerate(argv)
    )


def agent_hint() -> str | None:
    """Return the hint when an agent imports the SDK without having read the guide, else None."""
    try:
        if not running_under_coding_agent() or _running_the_cli() or skill_seen():
            return None
    except OSError:
        return None
    return AGENT_HINT


def print_agent_hint() -> None:
    hint = agent_hint()
    if hint:
        print(hint, file=sys.stderr)
