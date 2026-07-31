"""Tests for the automatic shortening of over-long datapoint contexts.

Shortening is on by default, so a context can be rewritten without the caller
asking for it — every one of these paths must be visible in the logs at warning
level.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from rapidata.rapidata_client.config import rapidata_config
from rapidata.rapidata_client.context.context_manager import (
    MAX_CONTEXT_LENGTH,
    ContextManager,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint


@pytest.fixture(autouse=True)
def restore_auto_shorten():
    original = rapidata_config.upload.autoShortenContext
    yield
    rapidata_config.upload.autoShortenContext = original


def _datapoint(context: str | None) -> Datapoint:
    return Datapoint(asset="image.jpg", data_type="media", context=context)


def _manager(shortened: list[str] | None = None) -> ContextManager:
    manager = ContextManager(MagicMock())
    if shortened is not None:
        manager.shorten_contexts = MagicMock(return_value=shortened)  # type: ignore[method-assign]
    return manager


def test_auto_shorten_is_on_by_default():
    assert rapidata_config.upload.autoShortenContext is True


def test_over_long_context_is_shortened_by_default(caplog):
    long_context = "a" * (MAX_CONTEXT_LENGTH + 1)
    datapoints = [_datapoint(long_context)]
    manager = _manager(shortened=["short context"])

    with caplog.at_level(logging.WARNING):
        manager._enforce_context_length(datapoints, question="Is this a cat?")

    manager.shorten_contexts.assert_called_once_with(  # type: ignore[attr-defined]
        [(long_context, "Is this a cat?")]
    )
    assert datapoints[0].context == "short context"
    assert "shortened automatically" in caplog.text


def test_context_within_limit_is_untouched(caplog):
    datapoints = [_datapoint("a" * MAX_CONTEXT_LENGTH), _datapoint(None)]
    manager = _manager(shortened=[])

    with caplog.at_level(logging.WARNING):
        manager._enforce_context_length(datapoints, question="Is this a cat?")

    manager.shorten_contexts.assert_not_called()  # type: ignore[attr-defined]
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


def test_empty_shortening_result_keeps_original_context(caplog):
    long_context = "a" * (MAX_CONTEXT_LENGTH + 1)
    datapoints = [_datapoint(long_context)]
    manager = _manager(shortened=[""])

    with caplog.at_level(logging.WARNING):
        manager._enforce_context_length(datapoints, question="Is this a cat?")

    assert datapoints[0].context == long_context
    assert "empty result" in caplog.text


def test_without_question_context_is_left_unchanged(caplog):
    long_context = "a" * (MAX_CONTEXT_LENGTH + 1)
    datapoints = [_datapoint(long_context)]
    manager = _manager(shortened=["short context"])

    with caplog.at_level(logging.WARNING):
        manager._enforce_context_length(datapoints, question=None)

    manager.shorten_contexts.assert_not_called()  # type: ignore[attr-defined]
    assert datapoints[0].context == long_context
    assert "no question/instruction was available" in caplog.text


def test_disabled_auto_shorten_only_warns(caplog):
    rapidata_config.upload.autoShortenContext = False
    long_context = "a" * (MAX_CONTEXT_LENGTH + 1)
    datapoints = [_datapoint(long_context)]
    manager = _manager(shortened=["short context"])

    with caplog.at_level(logging.WARNING):
        manager._enforce_context_length(datapoints, question="Is this a cat?")

    manager.shorten_contexts.assert_not_called()  # type: ignore[attr-defined]
    assert datapoints[0].context == long_context
    assert "automatic shortening is turned off" in caplog.text
