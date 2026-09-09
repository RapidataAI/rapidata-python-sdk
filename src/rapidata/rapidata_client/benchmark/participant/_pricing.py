from __future__ import annotations

import math
from typing import Literal, get_args

from rapidata.api_client.models.cost_unit import CostUnit

PriceUnit = Literal["image", "video_second", "million_tokens"]
"""The unit a participant's price is quoted in, always in USD."""

_UNIT_TO_COST_UNIT: dict[PriceUnit, CostUnit] = {
    "image": CostUnit.USDPERIMAGE,
    "video_second": CostUnit.USDPERVIDEOSECOND,
    "million_tokens": CostUnit.USDPERMILLIONTOKENS,
}

_COST_UNIT_TO_UNIT: dict[CostUnit, PriceUnit] = {
    cost_unit: unit for unit, cost_unit in _UNIT_TO_COST_UNIT.items()
}


def validate_price(price: float, unit: PriceUnit) -> tuple[float, CostUnit]:
    """Checks a price/unit pair and returns it in the backend's representation.

    Raises:
        ValueError: If the price is not a finite number greater than zero or the
            unit is not one of :data:`PriceUnit`.
    """
    # bool is an int subclass, so `True` would otherwise pass as a price of 1.
    if isinstance(price, bool) or not isinstance(price, (int, float)):
        raise ValueError("price must be a number")
    if not math.isfinite(price) or price <= 0:
        raise ValueError("price must be a finite number greater than 0")

    cost_unit = _UNIT_TO_COST_UNIT.get(unit)
    if cost_unit is None:
        allowed = ", ".join(repr(u) for u in get_args(PriceUnit))
        raise ValueError(f"unit must be one of {allowed}, got {unit!r}")

    return float(price), cost_unit


def to_price_unit(cost_unit: CostUnit | None) -> PriceUnit | None:
    """Maps the backend's cost unit back to the SDK's unit name."""
    if cost_unit is None:
        return None
    return _COST_UNIT_TO_UNIT[CostUnit(cost_unit)]
