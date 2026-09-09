"""Tests for participant pricing.

A priced participant appears on the benchmark's score-vs-cost chart. The price
is set on an existing participant through ``PATCH /participant/{id}`` with
``cost`` and ``costUnit``; clearing requires both fields to be sent as explicit
nulls, because an omitted field means "leave unchanged".
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from rapidata.api_client.models.cost_unit import CostUnit
from rapidata.api_client.models.participant_status import ParticipantStatus
from rapidata.rapidata_client.benchmark.participant.participant import (
    BenchmarkParticipant,
)
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark


def _make_participant() -> BenchmarkParticipant:
    return BenchmarkParticipant(
        name="model-a",
        id="p-0",
        openapi_service=MagicMock(),
        benchmark_id="bm-1",
    )


def _make_benchmark() -> RapidataBenchmark:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    return RapidataBenchmark("bm", "bm-1", svc)


def _patch_payload(participant: BenchmarkParticipant):
    patch = (
        participant._openapi_service.leaderboard.participant_api.participant_participant_id_patch
    )
    patch.assert_called_once()
    assert patch.call_args.kwargs["participant_id"] == "p-0"
    return patch.call_args.kwargs["update_participant_endpoint_input"]


@pytest.mark.parametrize(
    ("unit", "cost_unit"),
    [
        ("image", CostUnit.USDPERIMAGE),
        ("video_second", CostUnit.USDPERVIDEOSECOND),
        ("million_tokens", CostUnit.USDPERMILLIONTOKENS),
    ],
)
def test_set_price_maps_unit_and_patches_cost(unit, cost_unit) -> None:
    participant = _make_participant()

    participant.set_price(0.04, unit)

    payload = _patch_payload(participant)
    assert payload.cost == 0.04
    assert payload.cost_unit == cost_unit
    # Only the price fields travel; an omitted field leaves e.g. the name untouched.
    assert payload.to_dict() == {"cost": 0.04, "costUnit": cost_unit.value}
    assert participant.price == 0.04
    assert participant.price_unit == unit


def test_set_price_accepts_int_and_stores_float() -> None:
    participant = _make_participant()

    participant.set_price(3, "million_tokens")

    assert _patch_payload(participant).cost == 3.0
    assert participant.price == 3.0


@pytest.mark.parametrize(
    "price", [0, -1.5, True, float("nan"), float("inf"), "0.04", None]
)
def test_set_price_rejects_invalid_price(price) -> None:
    participant = _make_participant()

    with pytest.raises(ValueError):
        participant.set_price(price, "image")

    participant._openapi_service.leaderboard.participant_api.participant_participant_id_patch.assert_not_called()
    assert participant.price is None


@pytest.mark.parametrize("unit", ["images", "UsdPerImage", "token", "", None])
def test_set_price_rejects_unknown_unit(unit) -> None:
    participant = _make_participant()

    with pytest.raises(ValueError):
        participant.set_price(0.04, unit)

    participant._openapi_service.leaderboard.participant_api.participant_participant_id_patch.assert_not_called()


def test_clear_price_sends_explicit_nulls() -> None:
    participant = BenchmarkParticipant(
        name="model-a",
        id="p-0",
        openapi_service=MagicMock(),
        benchmark_id="bm-1",
        price=0.04,
        price_unit="image",
    )

    participant.clear_price()

    payload = _patch_payload(participant)
    assert payload.cost is None
    assert payload.cost_unit is None
    assert payload.to_dict() == {"cost": None, "costUnit": None}
    assert participant.price is None
    assert participant.price_unit is None


def test_participants_expose_price_from_backend() -> None:
    benchmark = _make_benchmark()
    item = MagicMock()
    item.name, item.id, item.status = "model-a", "p-0", ParticipantStatus.SUBMITTED
    item.cost, item.cost_unit = 2.5, CostUnit.USDPERMILLIONTOKENS
    unpriced = MagicMock()
    unpriced.name, unpriced.id, unpriced.status = (
        "model-b",
        "p-1",
        ParticipantStatus.CREATED,
    )
    unpriced.cost, unpriced.cost_unit = None, None
    benchmark._openapi_service.leaderboard.benchmark_api.benchmark_benchmark_id_participants_get.return_value.items = [
        item,
        unpriced,
    ]

    priced, without = benchmark.participants

    assert (priced.price, priced.price_unit) == (2.5, "million_tokens")
    assert (without.price, without.price_unit) == (None, None)
