"""Tests for reading the current billing period.

The period overview and the billing summary are two separate endpoints, and the
manager's job is to fold them into one object: costs come from the period,
credits and the spending cap from the organization's billing account.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from rapidata.rapidata_client.billing.rapidata_billing_manager import (
    RapidataBillingManager,
)

START = datetime(2026, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _manager(
    available_amount: float | None = 42.5,
    effective_limit: float | None = 500.0,
    gross_cost: float = 100.0,
    discount: float = 10.0,
    net_cost: float = 90.0,
) -> RapidataBillingManager:
    openapi_service = MagicMock()
    billing_api = openapi_service.payment.billing_api
    billing_api.billing_summary_get.return_value = MagicMock(
        available_amount=available_amount,
        effective_limit=effective_limit,
    )
    billing_api.billing_period_active_get.return_value = MagicMock(
        id="billing_period_id",
        start_date=START,
        end_date=END,
        status=MagicMock(value="Open"),
        total_gross_cost=gross_cost,
        total_discount=discount,
        total_net_cost=net_cost,
        total_response_count=1234,
    )
    return RapidataBillingManager(openapi_service=openapi_service)


def test_get_current_billing_period_reports_costs_and_credits():
    period = _manager().get_current_billing_period()

    assert period.id == "billing_period_id"
    assert period.start_date == START
    assert period.end_date == END
    assert period.status == "Open"
    assert period.gross_cost == 100.0
    assert period.discount == 10.0
    assert period.outstanding_cost == 90.0
    assert period.response_count == 1234
    assert period.credits == 42.5
    assert period.effective_limit == 500.0


def test_amounts_are_rounded_to_the_cent():
    """Per-response accrual produces far more decimals than money has."""
    period = _manager(
        available_amount=7.129999999,
        effective_limit=500.005,
        gross_cost=100.123456,
        discount=10.987654,
        net_cost=89.135802,
    ).get_current_billing_period()

    assert period.gross_cost == 100.12
    assert period.discount == 10.99
    assert period.outstanding_cost == 89.14
    assert period.credits == 7.13
    assert period.effective_limit == 500.0


def test_credits_and_limit_are_none_when_unset():
    """A usage-billed organization has no prepaid balance and no cap."""
    period = _manager(
        available_amount=None, effective_limit=None
    ).get_current_billing_period()

    assert period.credits is None
    assert period.effective_limit is None


def test_api_errors_propagate():
    from rapidata.rapidata_client.exceptions import RapidataError

    manager = _manager()
    manager._openapi_service.payment.billing_api.billing_period_active_get.side_effect = RapidataError(
        status_code=404, message="No active billing period found"
    )

    with pytest.raises(RapidataError):
        manager.get_current_billing_period()
