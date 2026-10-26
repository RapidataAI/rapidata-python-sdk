from __future__ import annotations

import json
import weakref
from typing import TYPE_CHECKING, Any

from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.job._revision_body import _as_dict
from rapidata.rapidata_client.exceptions.low_response_count_error import (
    MIN_RESPONSES_PER_DATAPOINT,
    LowResponseCountError,
)

if TYPE_CHECKING:
    from rapidata.api_client.models.i_order_workflow_input import IOrderWorkflowInput
    from rapidata.service.openapi_service import OpenAPIService

_LOW_RESPONSE_COUNT_CAPABILITY = "LowResponseCount"

# Only grants are cached: an organization enabled mid-session works without a new client.
_granted: weakref.WeakKeyDictionary[OpenAPIService, bool] = weakref.WeakKeyDictionary()


def ensure_response_count_allowed(
    openapi_service: OpenAPIService,
    workflow: IOrderWorkflowInput,
    responses: int,
) -> None:
    """Raise LowResponseCountError before anything is uploaded.

    Only simple workflows are gated, as on the backend; ranking is not.
    """
    if responses >= MIN_RESPONSES_PER_DATAPOINT:
        return
    if _as_dict(workflow).get("_t") != "SimpleWorkflow":
        return
    if _low_response_count_allowed(openapi_service) is False:
        raise LowResponseCountError(responses)


def _low_response_count_allowed(openapi_service: OpenAPIService) -> bool | None:
    """None when the lookup failed, which leaves the decision to the backend."""
    if _granted.get(openapi_service):
        return True

    from rapidata.rapidata_client.api.rapidata_api_client import (
        suppress_rapidata_error_logging,
    )

    try:
        with suppress_rapidata_error_logging():
            response = openapi_service.api_client.call_api(
                "GET",
                f"https://auth.{openapi_service.environment}/connect/userinfo",
                _request_timeout=5,
            )
        if response.status != 200:
            raise RuntimeError(f"userinfo returned {response.status}")
        userinfo: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        logger.debug("Capability lookup failed, the backend decides: %s", e)
        return None

    allowed = _LOW_RESPONSE_COUNT_CAPABILITY in _claim_values(
        userinfo, "capabilities"
    ) or "admin" in _claim_values(userinfo, "platform_relations")
    if allowed:
        _granted[openapi_service] = True
    return allowed


def _claim_values(userinfo: dict[str, Any], claim: str) -> list[str]:
    # A claim with a single value comes back as a bare string.
    value = userinfo.get(claim)
    if isinstance(value, str):
        return [value]
    return value if isinstance(value, list) else []
