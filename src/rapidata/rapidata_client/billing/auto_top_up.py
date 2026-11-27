from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.api_client.models.get_auto_top_up_endpoint_output import (
        GetAutoTopUpEndpointOutput,
    )


@dataclass(frozen=True)
class AutoTopUp:
    """The automatic top-up settings of a prepaid organization.

    While enabled, the saved card is charged ``amount`` whenever the prepaid
    balance falls below ``threshold``. All amounts are in US dollars.

    Attributes:
        enabled: Whether the saved card is charged automatically when the
            balance runs low.
        threshold: The balance below which the saved card is charged, or
            ``None`` when automatic top-ups were never configured.
        amount: What each automatic top-up adds to the balance, or ``None``
            when automatic top-ups were never configured.
        card_brand: The brand of the saved card, such as ``"visa"``, or
            ``None`` when no card is saved.
        card_last4: The last four digits of the saved card, or ``None`` when
            no card is saved.
        failed_at: When a declined charge paused automatic top-ups, or
            ``None`` when none did. The card stays saved; configuring
            automatic top-ups again resumes them.
    """

    enabled: bool
    threshold: float | None
    amount: float | None
    card_brand: str | None
    card_last4: str | None
    failed_at: datetime | None

    @classmethod
    def _from_model(cls, model: GetAutoTopUpEndpointOutput) -> AutoTopUp:
        return cls(
            enabled=model.enabled,
            threshold=model.threshold,
            amount=model.amount,
            card_brand=model.card_brand,
            card_last4=model.card_last4,
            failed_at=model.failed_at,
        )
