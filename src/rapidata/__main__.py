"""``python -m rapidata`` — utilities that do not need an authenticated client.

``python -m rapidata skill`` prints the maintained agent skill for this SDK;
``--install`` writes it into the current project so a coding agent loads it on
every session instead of reading the installed source.

``python -m rapidata status`` reports whether this machine can authenticate
without starting a login; ``python -m rapidata login`` runs the browser login
and saves the credentials that ``RapidataClient()`` reuses.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

from rapidata import __version__
from rapidata._agent_hint import (
    AGENT_DOCS_URL,
    LLMS_FULL_URL,
    SKILL_INSTALL_PATHS,
    SKILL_RAW_URL,
    mark_skill_read,
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


def _environment(arg: str | None) -> str:
    return arg or os.environ.get("RAPIDATA_ENVIRONMENT") or "rapidata.ai"


def _credential_manager(environment: str):
    from rapidata.service.credential_manager import CredentialManager
    from rapidata.service.openapi_service import _get_local_certificate

    cert_path = _get_local_certificate() if environment == "rapidata.dev" else None
    return CredentialManager(
        endpoint=f"https://auth.{environment}", cert_path=cert_path
    )


def _auth_source(environment: str) -> str | None:
    if os.environ.get("RAPIDATA_TOKEN_FILE"):
        return f"the token file in RAPIDATA_TOKEN_FILE ({os.environ['RAPIDATA_TOKEN_FILE']})"
    if os.environ.get("RAPIDATA_CLIENT_ID") and os.environ.get(
        "RAPIDATA_CLIENT_SECRET"
    ):
        return "RAPIDATA_CLIENT_ID / RAPIDATA_CLIENT_SECRET"
    credential = _credential_manager(environment).stored_credential()
    if credential:
        return f"saved credentials ({credential.get_display_string()})"
    return None


def status(environment: str) -> int:
    source = _auth_source(environment)
    if source:
        print(f"Authenticated for {environment} via {source}.")
        return 0
    print(
        f"Not logged in to {environment}. Run `python -m rapidata login` to log in "
        "in the browser, or set RAPIDATA_CLIENT_ID and RAPIDATA_CLIENT_SECRET."
    )
    return 1


def login(environment: str) -> int:
    source = _auth_source(environment)
    if source:
        print(f"Already authenticated for {environment} via {source}.")
        return 0
    credential = _credential_manager(environment).get_client_credentials()
    if not credential:
        print(
            "Login did not complete. Run `python -m rapidata login` again.",
            file=sys.stderr,
        )
        return 1
    print(f"Logged in to {environment}. RapidataClient() now reuses these credentials.")
    return 0


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
    for name, help_text in (
        (
            "login",
            "log in through the browser and save credentials for RapidataClient()",
        ),
        ("status", "report whether this machine can authenticate, without logging in"),
    ):
        auth = sub.add_parser(name, help=help_text)
        auth.add_argument(
            "--environment",
            help="Rapidata environment (default: RAPIDATA_ENVIRONMENT, else rapidata.ai)",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "login":
        return login(_environment(args.environment))
    if args.command == "status":
        return status(_environment(args.environment))
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

    mark_skill_read()
    if args.install:
        target = install_skill(args.dir, args.agent, content)
        print(f"Installed the Rapidata skill to {target}")
        return 0

    print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
