from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.get_outstanding_cost_endpoint_output import (
        GetOutstandingCostEndpointOutput,
    )


@dataclass(frozen=True)
class OutstandingBalance:
    """What the organization currently owes, across finalized and settled periods.

    This is a snapshot of everything already due — unpaid invoices plus periods
    that have ended and settled but are not yet invoiced. The current,
    still-accruing period is reported separately in ``current_period_accrued``
    and is *not* part of ``total_outstanding``: nothing is due until a period
    ends and settles.

    All amounts are in US dollars, rounded to the cent.

    Attributes:
        total_outstanding: The total currently owed — ``unpaid_invoices_amount``
            plus ``awaiting_invoice_amount``. Excludes the current period.
        unpaid_invoices_amount: The amount owed on finalized invoices that have
            not been paid.
        unpaid_invoice_count: How many unpaid invoices make up
            ``unpaid_invoices_amount``.
        awaiting_invoice_amount: The settled cost of ended periods that have not
            been invoiced yet.
        awaiting_invoice_period_count: How many periods make up
            ``awaiting_invoice_amount``.
        current_period_accrued: Billable spend accrued in the current, still-open
            period. Not part of ``total_outstanding``.
        currency: The currency the amounts are in, or ``None`` when nothing is
            outstanding.
        settlement_stale: ``True`` when a period behind ``awaiting_invoice_amount``
            is awaiting a settlement recompute, so that figure may still change.
    """

    total_outstanding: float
    unpaid_invoices_amount: float
    unpaid_invoice_count: int
    awaiting_invoice_amount: float
    awaiting_invoice_period_count: int
    current_period_accrued: float
    currency: str | None
    settlement_stale: bool

    @classmethod
    def _from_model(cls, model: GetOutstandingCostEndpointOutput) -> OutstandingBalance:
        return cls(
            total_outstanding=round(model.total_outstanding, 2),
            unpaid_invoices_amount=round(model.unpaid_invoices_amount, 2),
            unpaid_invoice_count=model.unpaid_invoice_count,
            awaiting_invoice_amount=round(model.awaiting_invoice_amount, 2),
            awaiting_invoice_period_count=model.awaiting_invoice_period_count,
            current_period_accrued=round(model.current_period_accrued, 2),
            currency=model.currency,
            settlement_stale=model.settlement_stale,
        )
