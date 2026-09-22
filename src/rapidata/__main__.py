"""``python -m rapidata`` — utilities that do not need an authenticated client.

``python -m rapidata skill`` prints the maintained agent skill for this SDK;
``--install`` writes it into the current project so a coding agent loads it on
every session instead of reading the installed source.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

from rapidata import __version__
from rapidata.rapidata_client.config._agent_hint import (
    AGENT_DOCS_URL,
    LLMS_FULL_URL,
    SKILL_INSTALL_PATHS,
    SKILL_RAW_URL,
)


def fetch_skill(timeout: float = 10) -> str:
    response = requests.get(SKILL_RAW_URL, timeout=timeout)
    response.raise_for_status()
    return response.text


def install_skill(root: Path, agent: str, content: str) -> Path:
    target = root / SKILL_INSTALL_PATHS[agent]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m rapidata",
        description=f"Rapidata SDK {__version__}. Agent guide: {AGENT_DOCS_URL}",
    )
    sub = parser.add_subparsers(dest="command")
    skill = sub.add_parser(
        "skill",
        help="print the agent skill for this SDK, or install it into the project",
    )
    skill.add_argument(
        "--install",
        action="store_true",
        help="write the skill into the current project instead of printing it",
    )
    skill.add_argument(
        "--agent",
        choices=sorted(SKILL_INSTALL_PATHS),
        default="claude",
        help="which agent's project-local skill path to write to (default: claude)",
    )
    skill.add_argument(
        "--dir",
        type=Path,
        default=Path.cwd(),
        help="project root to install into (default: current directory)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command != "skill":
        parser.print_help()
        return 0

    try:
        content = fetch_skill()
    except requests.RequestException as e:
        print(f"Could not fetch the skill ({e}).", file=sys.stderr)
        print(
            f"Read it online instead: {SKILL_RAW_URL} or {LLMS_FULL_URL}",
            file=sys.stderr,
        )
        return 1

    if args.install:
        target = install_skill(args.dir, args.agent, content)
        print(f"Installed the Rapidata skill to {target}")
        return 0

    print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
