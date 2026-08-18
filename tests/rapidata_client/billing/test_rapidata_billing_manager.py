"""Tests for reading the current billing period.

The period overview and the billing summary are two separate endpoints, and the
manager's job is to fold them into one object: costs come from the period,
credits from the organization's billing account.
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


def _manager(available_amount: float | None) -> RapidataBillingManager:
    openapi_service = MagicMock()
    billing_api = openapi_service.payment.billing_api
    billing_api.billing_summary_get.return_value = MagicMock(
        available_amount=available_amount
    )
    billing_api.billing_period_active_get.return_value = MagicMock(
        id="billing_period_id",
        start_date=START,
        end_date=END,
        status=MagicMock(value="Open"),
        total_gross_cost=100.0,
        total_discount=10.0,
        total_net_cost=90.0,
        total_response_count=1234,
    )
    return RapidataBillingManager(openapi_service=openapi_service)


def test_get_current_billing_period_reports_costs_and_credits():
    period = _manager(available_amount=42.5).get_current_billing_period()

    assert period.id == "billing_period_id"
    assert period.start_date == START
    assert period.end_date == END
    assert period.status == "Open"
    assert period.gross_cost == 100.0
    assert period.discount == 10.0
    assert period.outstanding_cost == 90.0
    assert period.response_count == 1234
    assert period.credits == 42.5


def test_credits_are_none_when_the_organization_is_not_prepaid():
    """A usage-billed organization has no prepaid balance to report."""
    assert _manager(available_amount=None).get_current_billing_period().credits is None


def test_api_errors_propagate():
    from rapidata.rapidata_client.exceptions import RapidataError

    manager = _manager(available_amount=0.0)
    manager._openapi_service.payment.billing_api.billing_period_active_get.side_effect = RapidataError(
        status_code=404, message="No active billing period found"
    )

    with pytest.raises(RapidataError):
        manager.get_current_billing_period()
