from __future__ import annotations

"""Helpers for printing a terminal-friendly QR code that links to the public
campaign preview page.

The QR code is a convenience nudge so the user can open the preview on a phone
without copy-pasting the URL. All functions here are best-effort: failures are
logged at debug level and never raised to the caller, so order / job execution
is never affected by QR rendering problems.
"""

from time import sleep
from typing import TYPE_CHECKING, cast

from rapidata.rapidata_client.config.logger import logger
from rapidata.rapidata_client.config.managed_print import managed_print
from rapidata.rapidata_client.config.rapidata_config import rapidata_config

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService


_PREVIEW_URL_TEMPLATE = "https://rapids.{environment}/preview/campaign?id={campaign_id}"


def build_campaign_preview_url(environment: str, campaign_id: str) -> str:
    """Return the public preview URL for the given campaign."""
    return _PREVIEW_URL_TEMPLATE.format(
        environment=environment, campaign_id=campaign_id
    )


def print_campaign_preview_qr(environment: str, campaign_id: str) -> None:
    """Print a terminal QR code that links to the campaign preview page.

    Respects ``rapidata_config.logging.silent_mode``. If QR rendering fails for
    any reason we still surface the preview URL via ``managed_print`` so the
    user can open it manually.

    Args:
        environment: The Rapidata environment (e.g. ``rapidata.ai``).
        campaign_id: The id of the campaign to preview. For orders this is the
            order's campaign id; for job definitions it's the preview
            (distilling) campaign id.
    """
    if rapidata_config.logging.silent_mode:
        return

    url = build_campaign_preview_url(environment, campaign_id)

    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_L

        qr = qrcode.QRCode(
            error_correction=ERROR_CORRECT_L,
            border=1,
            box_size=1,
        )
        qr.add_data(url)
        qr.make(fit=True)

        managed_print(f"Preview the campaign ({url}):")
        qr.print_ascii(invert=True)
    except Exception:
        logger.debug(
            "Failed to render campaign preview QR code for %s",
            url,
            exc_info=True,
        )
        managed_print(f"Preview the campaign at: {url}")


def _resolve_campaign_id_from_pipeline(
    openapi_service: "OpenAPIService",
    pipeline_id: str,
    max_retries: int = 5,
    retry_delay: float = 1.0,
) -> str | None:
    """Pull the campaign id out of a pipeline's ``campaign-artifact``.

    Pipeline artifacts are populated asynchronously after creation, so we
    retry a few times before giving up. Returns ``None`` if the artifact never
    materialises.
    """
    from rapidata.api_client.models.campaign_artifact_model import (
        CampaignArtifactModel,
    )

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            pipeline = (
                openapi_service.pipeline.pipeline_api.pipeline_pipeline_id_get(
                    pipeline_id
                )
            )
            artifact = pipeline.artifacts.get("campaign-artifact")
            if artifact is not None:
                return cast(
                    CampaignArtifactModel, artifact.actual_instance
                ).campaign_id
        except Exception as e:
            last_exc = e

        if attempt < max_retries - 1:
            sleep(retry_delay)

    logger.debug(
        "Could not resolve campaign id from pipeline '%s' after %d attempts",
        pipeline_id,
        max_retries,
        exc_info=last_exc,
    )
    return None


def print_campaign_preview_qr_for_pipeline(
    openapi_service: "OpenAPIService", pipeline_id: str
) -> None:
    """Fetch the campaign id from the given pipeline and print a preview QR code.

    Best-effort: any failure is swallowed with a debug log so callers never
    need to guard this call. Also a no-op in silent mode.

    Args:
        openapi_service: The OpenAPI service used to look up the pipeline.
        pipeline_id: The id of the pipeline whose ``campaign-artifact`` should
            be used for the preview.
    """
    if rapidata_config.logging.silent_mode:
        return

    campaign_id = _resolve_campaign_id_from_pipeline(openapi_service, pipeline_id)
    if not campaign_id:
        return

    print_campaign_preview_qr(
        environment=openapi_service.environment, campaign_id=campaign_id
    )
