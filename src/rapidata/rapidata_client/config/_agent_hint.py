"""One-time pointer to the SDK guide when a coding agent is driving the process.

Agents that ``pip install rapidata`` tend to read this source tree instead of
the maintained skill and end up reconstructing usage from internals. They do
read their own script output, so the client prints the pointer once per
process when it detects an agent runtime.
"""

from __future__ import annotations

import os
from pathlib import Path

SKILL_RAW_URL = "https://raw.githubusercontent.com/RapidataAI/skills/main/plugins/rapidata-sdk-plugin/skills/rapidata/SKILL.md"
LLMS_FULL_URL = "https://docs.rapidata.ai/llms-full.txt"
AGENT_DOCS_URL = "https://docs.rapidata.ai/ai_agents/"

# Env vars set by the agent runtimes we know. Truthiness is enough: Claude Code
# exports CLAUDECODE=1, Cursor exports CURSOR_AGENT=1, Codex exports
# CODEX_SANDBOX, Gemini CLI exports GEMINI_CLI=1.
_AGENT_ENV_VARS = (
    "CLAUDECODE",
    "CLAUDE_CODE",
    "CURSOR_AGENT",
    "CODEX_SANDBOX",
    "GEMINI_CLI",
)

AGENT_HINT = (
    "Coding agent detected. Read the Rapidata SDK guide before writing code, "
    "do not infer usage from the installed source:\n"
    "  python -m rapidata skill            # print the guide\n"
    "  python -m rapidata skill --install  # install it for this project\n"
    f"  {LLMS_FULL_URL}\n"
    "Set RAPIDATA_AGENT_HINT=0 to silence this message."
)

# Where each agent picks up a project-local skill file, relative to the project root.
SKILL_INSTALL_PATHS: dict[str, str] = {
    "claude": ".claude/skills/rapidata/SKILL.md",
    "cursor": ".cursor/rules/rapidata.mdc",
    "codex": ".codex/skills/rapidata/SKILL.md",
    "generic": "AGENTS.md",
}

_hint_shown = False


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
    return any(os.environ.get(var) for var in _AGENT_ENV_VARS)


def skill_installed(root: Path | None = None) -> bool:
    """Return True when a project-local copy of the skill exists under ``root`` (default: cwd)."""
    root = root or Path.cwd()
    return any((root / rel).is_file() for rel in SKILL_INSTALL_PATHS.values())


def agent_hint_once() -> str | None:
    """Return the hint the first time it is asked for in an agent process without the skill, else None."""
    global _hint_shown
    if _hint_shown or not running_under_coding_agent() or skill_installed():
        return None
    _hint_shown = True
    return AGENT_HINT
