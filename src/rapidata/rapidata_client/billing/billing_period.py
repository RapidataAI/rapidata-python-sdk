from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.get_active_billing_period_overview_endpoint_output import (
        GetActiveBillingPeriodOverviewEndpointOutput,
    )
    from rapidata.api_client.models.get_billing_summary_endpoint_output import (
        GetBillingSummaryEndpointOutput,
    )


def _to_cents(amount: float | int | None) -> float | None:
    """Round a dollar amount to the cent the invoice will actually charge.

    The backend accrues cost per response, so a raw total carries far more
    decimals than money has — rounding here keeps the reported figures
    printable without every caller doing it.
    """
    return None if amount is None else round(amount, 2)


@dataclass(frozen=True)
class BillingPeriod:
    """What the current billing period has cost so far, and what is left to spend.

    All amounts are in US dollars, rounded to the cent. Costs accrue
    continuously while jobs run, so this is a snapshot: fetch it again for an
    up-to-date figure.

    Attributes:
        id: The billing period's id.
        start_date: When the billing period started.
        end_date: When the billing period ends.
        status: The period's lifecycle status — ``"Open"`` while it is still
            accruing cost, and one of ``"Invoiced"``, ``"Void"``,
            ``"Reconciling"``, ``"PendingReview"`` or ``"Closed"`` afterwards.
        outstanding_cost: The net cost accrued so far — ``gross_cost`` minus
            ``discount``. This is what the period would be invoiced for today.
        gross_cost: The cost accrued so far, before any discounts.
        discount: The discounts applied to the period so far.
        response_count: The number of billable responses collected in the period.
        credits: The prepaid credit still available to spend, or ``None`` when the
            organization is not on a prepaid plan (it is billed for its usage
            instead). Credits are an organization-level balance rather than a
            property of the period, so they carry across periods until used up.
        effective_limit: The most the organization may spend in this period, or
            ``None`` when it spends without a cap. Vouchers raise it, so on a
            prepaid plan this is the total credit granted and ``credits`` is
            what remains of it.
    """

    id: str
    start_date: datetime
    end_date: datetime
    status: str
    outstanding_cost: float
    gross_cost: float
    discount: float
    response_count: int
    credits: float | None
    effective_limit: float | None

    @classmethod
    def _from_models(
        cls,
        overview: GetActiveBillingPeriodOverviewEndpointOutput,
        summary: GetBillingSummaryEndpointOutput,
    ) -> BillingPeriod:
        return cls(
            id=overview.id,
            start_date=overview.start_date,
            end_date=overview.end_date,
            status=overview.status.value,
            outstanding_cost=round(overview.total_net_cost, 2),
            gross_cost=round(overview.total_gross_cost, 2),
            discount=round(overview.total_discount, 2),
            response_count=overview.total_response_count,
            credits=_to_cents(summary.available_amount),
            effective_limit=_to_cents(summary.effective_limit),
        )
