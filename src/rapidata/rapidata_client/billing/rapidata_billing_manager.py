from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.billing.billing_period import BillingPeriod
from rapidata.rapidata_client.config import logger, tracer

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService


class RapidataBillingManager:
    """Read what the current billing period has cost and what credit is left.

    Billing is settled per organization, so the figures cover everything the
    organization spent, not only the jobs this client created.

    Access this manager via :py:attr:`RapidataClient.billing`.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        logger.debug("RapidataBillingManager initialized")

    def get_current_billing_period(self) -> BillingPeriod:
        """Get the billing period that is currently accruing cost.

        Returns:
            BillingPeriod: The current period, its outstanding cost and the
                remaining prepaid credits.

        Raises:
            RapidataError: With status 404 if the organization has no active
                billing period — a period only opens once there is something
                to bill.
        """
        with tracer.start_as_current_span(
            "RapidataBillingManager.get_current_billing_period"
        ):
            billing_api = self._openapi_service.payment.billing_api
            # Credits live on the organization's billing account, not on the
            # period, so they come from the summary rather than the overview.
            summary = billing_api.billing_summary_get()
            overview = billing_api.billing_period_active_get()
            return BillingPeriod._from_models(overview, summary)
