"""Tests for the shortening of datapoint contexts before upload.

An over-long context is always shortened — that path cannot be opted out of, so
it must be visible in the logs at warning level. Shortening contexts that
already fit is opt-in via ``rapidata_config.upload.contextShortening``.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from rapidata.rapidata_client.config import rapidata_config
from rapidata.rapidata_client.context.context_manager import (
    MAX_CONTEXT_LENGTH,
    SHORTEN_BATCH_SIZE,
    ContextManager,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint

QUESTION = "Is this a cat?"
LONG_CONTEXT = "a" * (MAX_CONTEXT_LENGTH + 1)
SHORT_CONTEXT = "a short context"


@pytest.fixture(autouse=True)
def restore_context_shortening():
    original = rapidata_config.upload.contextShortening
    yield
    rapidata_config.upload.contextShortening = original


def _datapoint(context: str | None) -> Datapoint:
    return Datapoint(asset="image.jpg", data_type="media", context=context)


def _manager(shortened: list[str] | None = None) -> ContextManager:
    manager = ContextManager(MagicMock())
    if shortened is not None:
        manager.shorten_contexts = MagicMock(return_value=shortened)  # type: ignore[method-assign]
    return manager


def _warnings(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def _stub_endpoint(manager: ContextManager) -> MagicMock:
    """Stub the shorten-context endpoint to echo ``short:<context>`` per item."""

    def shorten(shorten_context_endpoint_input):
        return MagicMock(
            items=[
                MagicMock(shortened_context=f"short:{item.context}")
                for item in shorten_context_endpoint_input.items
            ]
        )

    endpoint = MagicMock(side_effect=shorten)
    manager._openapi_service.dataset.context_shortening_api.datasets_shorten_context_post = (  # type: ignore[attr-defined]
        endpoint
    )
    return endpoint


def test_context_shortening_is_off_by_default():
    assert rapidata_config.upload.contextShortening is False


def test_over_long_context_is_always_shortened(caplog):
    datapoints = [_datapoint(LONG_CONTEXT)]
    manager = _manager(shortened=["shortened context"])

    with caplog.at_level(logging.INFO):
        manager._apply_context_shortening(datapoints, question=QUESTION)

    manager.shorten_contexts.assert_called_once_with([(LONG_CONTEXT, QUESTION)])  # type: ignore[attr-defined]
    assert datapoints[0].context == "shortened context"
    assert any("exceed the maximum" in message for message in _warnings(caplog))
    assert "shortened context from 401 to 17 characters" in caplog.text


def test_context_within_limit_is_untouched_when_disabled(caplog):
    datapoints = [_datapoint(SHORT_CONTEXT), _datapoint(None)]
    manager = _manager(shortened=[])

    with caplog.at_level(logging.INFO):
        manager._apply_context_shortening(datapoints, question=QUESTION)

    manager.shorten_contexts.assert_not_called()  # type: ignore[attr-defined]
    assert datapoints[0].context == SHORT_CONTEXT
    assert _warnings(caplog) == []


def test_enabled_shortens_every_context(caplog):
    datapoints = [_datapoint(SHORT_CONTEXT), _datapoint(LONG_CONTEXT), _datapoint(None)]
    rapidata_config.upload.contextShortening = True
    manager = _manager(shortened=["short one", "short two"])

    with caplog.at_level(logging.INFO):
        manager._apply_context_shortening(datapoints, question=QUESTION)

    manager.shorten_contexts.assert_called_once_with(  # type: ignore[attr-defined]
        [(SHORT_CONTEXT, QUESTION), (LONG_CONTEXT, QUESTION)]
    )
    assert [datapoint.context for datapoint in datapoints] == [
        "short one",
        "short two",
        None,
    ]
    # Only the over-long context is a rewrite the caller did not ask for, so it
    # alone is warned about; the per-datapoint detail stays at info.
    assert _warnings(caplog) == [
        f"1 context(s) exceed the maximum of {MAX_CONTEXT_LENGTH} characters and are "
        "being shortened for the instruction so the backend accepts them."
    ]
    assert "Datapoint 0: shortened context" in caplog.text


def test_empty_shortening_result_keeps_original_context(caplog):
    datapoints = [_datapoint(LONG_CONTEXT)]
    manager = _manager(shortened=[""])

    with caplog.at_level(logging.INFO):
        manager._apply_context_shortening(datapoints, question=QUESTION)

    assert datapoints[0].context == LONG_CONTEXT
    assert any("empty result" in message for message in _warnings(caplog))


def test_single_batch_is_sent_in_one_request():
    manager = ContextManager(MagicMock())
    endpoint = _stub_endpoint(manager)
    pairs = [(f"context {i}", QUESTION) for i in range(SHORTEN_BATCH_SIZE)]

    assert manager.shorten_contexts(pairs) == [
        f"short:context {i}" for i in range(SHORTEN_BATCH_SIZE)
    ]
    assert endpoint.call_count == 1


def test_large_batch_is_split_across_concurrent_requests():
    manager = ContextManager(MagicMock())
    endpoint = _stub_endpoint(manager)
    total = SHORTEN_BATCH_SIZE * 2 + 3
    pairs = [(f"context {i}", QUESTION) for i in range(total)]

    # Results must come back in input order regardless of which request finished first.
    assert manager.shorten_contexts(pairs) == [
        f"short:context {i}" for i in range(total)
    ]
    assert endpoint.call_count == 3
    # The requests run concurrently, so only the set of batch sizes is deterministic.
    assert sorted(
        len(call.kwargs["shorten_context_endpoint_input"].items)
        for call in endpoint.call_args_list
    ) == [3, SHORTEN_BATCH_SIZE, SHORTEN_BATCH_SIZE]
