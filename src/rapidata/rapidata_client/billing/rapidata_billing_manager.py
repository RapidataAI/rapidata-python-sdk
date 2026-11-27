from __future__ import annotations

from typing import TYPE_CHECKING

from rapidata.rapidata_client.billing.auto_top_up import AutoTopUp
from rapidata.rapidata_client.billing.billing_period import BillingPeriod
from rapidata.rapidata_client.config import logger, tracer

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService


class RapidataBillingManager:
    """Read what the current billing period has cost and what credit is left,
    and manage automatic top-ups of a prepaid balance.

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

    def get_outstanding_balance(self) -> float:
        """Get the total the organization currently owes, in US dollars.

        Covers finalized-but-unpaid invoices plus the settled cost of ended
        periods not yet invoiced. The current, still-accruing period is not
        part of this — nothing is due until a period ends and settles. The
        figure is already net of any voucher coverage and discounts.

        Returns:
            float: The total owed, in US dollars rounded to the cent. ``0.0``
                when the organization owes nothing.
        """
        with tracer.start_as_current_span(
            "RapidataBillingManager.get_outstanding_balance"
        ):
            billing_api = self._openapi_service.payment.billing_api
            outstanding = billing_api.billing_outstanding_get()
            return round(outstanding.total_outstanding, 2)

    def get_auto_top_up(self) -> AutoTopUp:
        """Get the organization's automatic top-up settings.

        Returns:
            AutoTopUp: Whether automatic top-ups are enabled, their threshold
                and amount, and the saved card.

        Raises:
            RapidataError: If the organization is not on a prepaid plan, or
                the caller is not one of its owners or admins.
        """
        with tracer.start_as_current_span("RapidataBillingManager.get_auto_top_up"):
            auto_top_up_api = self._openapi_service.payment.auto_top_up_api
            return AutoTopUp._from_model(auto_top_up_api.payment_auto_topup_get())

    def configure_auto_top_up(self, threshold: float, amount: float) -> str | None:
        """Charge the saved card ``amount`` whenever the prepaid balance falls below ``threshold``.

        Also resumes automatic top-ups that a declined charge paused.

        Args:
            threshold: The balance in US dollars below which the saved card is
                charged. Must be lower than ``amount``.
            amount: What each automatic top-up adds to the balance, in US
                dollars. At least 20, with at most two decimals.

        Returns:
            str | None: ``None`` when a card is already saved and the settings
                apply at once. Otherwise the url of a hosted checkout page:
                automatic top-ups only start once someone saves a card there.

        Raises:
            RapidataError: If the values break the rules above, the
                organization is not on a prepaid plan, or the caller is not
                one of its owners or admins.
        """
        from rapidata.api_client.models.configure_auto_top_up_endpoint_input import (
            ConfigureAutoTopUpEndpointInput,
        )

        with tracer.start_as_current_span(
            "RapidataBillingManager.configure_auto_top_up"
        ):
            auto_top_up_api = self._openapi_service.payment.auto_top_up_api
            output = auto_top_up_api.payment_auto_topup_put(
                ConfigureAutoTopUpEndpointInput(threshold=threshold, amount=amount)
            )
            return output.checkout_url

    def disable_auto_top_up(self) -> None:
        """Switch automatic top-ups off and remove the saved card.

        Raises:
            RapidataError: If the organization is not on a prepaid plan, or
                the caller is not one of its owners or admins.
        """
        with tracer.start_as_current_span("RapidataBillingManager.disable_auto_top_up"):
            auto_top_up_api = self._openapi_service.payment.auto_top_up_api
            auto_top_up_api.payment_auto_topup_delete()
