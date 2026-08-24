from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.billing.billing_period import BillingPeriod
from rapidata.rapidata_client.billing.outstanding_balance import OutstandingBalance
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

    def get_outstanding_balance(self) -> OutstandingBalance:
        """Get everything the organization currently owes.

        Covers finalized-but-unpaid invoices plus the settled cost of ended
        periods not yet invoiced. The current, still-accruing period is reported
        separately in :py:attr:`OutstandingBalance.current_period_accrued` and is
        not part of the total.

        Returns:
            OutstandingBalance: The total owed, broken down by unpaid invoices
                and periods awaiting an invoice.
        """
        with tracer.start_as_current_span(
            "RapidataBillingManager.get_outstanding_balance"
        ):
            billing_api = self._openapi_service.payment.billing_api
            outstanding = billing_api.billing_outstanding_get()
            return OutstandingBalance._from_model(outstanding)
