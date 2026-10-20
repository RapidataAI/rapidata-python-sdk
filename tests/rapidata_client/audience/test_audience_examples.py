"""Tests for listing and deleting an audience's qualification examples.

Deleting takes the example id, so get_examples has to expose it.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience


def _make_audience() -> tuple[RapidataAudience, MagicMock]:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    audience = RapidataAudience(
        id="aud-1", name="My Audience", filters=[], openapi_service=openapi_service
    )
    return audience, openapi_service


def test_delete_example_deletes_by_id_and_chains():
    audience, openapi_service = _make_audience()

    result = audience.delete_example("ex-1")

    openapi_service.audience.examples_api.audience_example_example_id_delete.assert_called_once_with(
        example_id="ex-1"
    )
    assert result is audience


def test_get_examples_exposes_the_id_delete_example_takes():
    audience, openapi_service = _make_audience()
    item = MagicMock(id="ex-1", context="A small blue book", truth=None)
    item.asset.actual_instance = None
    item.context_asset = None
    openapi_service.audience.examples_api.audience_audience_id_examples_get.return_value.items = [
        item
    ]

    examples = audience.get_examples()

    assert list(examples.columns) == [
        "id",
        "asset",
        "truth",
        "context",
        "contextAsset",
    ]
    assert examples["id"].tolist() == ["ex-1"]
