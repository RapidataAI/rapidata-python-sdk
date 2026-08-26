from __future__ import annotations

"""Helper for printing a terminal-friendly link to the dashboard preview page.

Best-effort: a no-op in silent mode. Never raises to the caller, so job
creation is never affected by preview-link problems.
"""

from rapidata.rapidata_client.config.managed_print import managed_print
from rapidata.rapidata_client.config.rapidata_config import rapidata_config


_APP_JOB_DEFINITION_URL_TEMPLATE = (
    "https://app.{environment}/definitions/{job_definition_id}"
)


def build_job_definition_preview_url(environment: str, job_definition_id: str) -> str:
    """Return the app URL for previewing the given job definition."""
    return _APP_JOB_DEFINITION_URL_TEMPLATE.format(
        environment=environment, job_definition_id=job_definition_id
    )


def print_job_definition_preview_link(environment: str, job_definition_id: str) -> None:
    """Print the app URL for previewing the given job definition."""
    if rapidata_config.logging.silent_mode:
        return

    url = build_job_definition_preview_url(environment, job_definition_id)
    managed_print(f"Preview in dashboard: {url}")
