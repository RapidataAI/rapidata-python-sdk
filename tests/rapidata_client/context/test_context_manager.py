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
    assert any("shortened context from" in message for message in _warnings(caplog))


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
    # The within-limit datapoint was shortened on request, so it stays at info;
    # only the over-long one warrants a warning.
    assert not any("Datapoint 0" in message for message in _warnings(caplog))
    assert any("Datapoint 1" in message for message in _warnings(caplog))


def test_empty_shortening_result_keeps_original_context(caplog):
    datapoints = [_datapoint(LONG_CONTEXT)]
    manager = _manager(shortened=[""])

    with caplog.at_level(logging.INFO):
        manager._apply_context_shortening(datapoints, question=QUESTION)

    assert datapoints[0].context == LONG_CONTEXT
    assert any("empty result" in message for message in _warnings(caplog))


def test_without_question_over_long_context_is_left_unchanged(caplog):
    datapoints = [_datapoint(LONG_CONTEXT)]
    manager = _manager(shortened=["shortened context"])

    with caplog.at_level(logging.INFO):
        manager._apply_context_shortening(datapoints, question=None)

    manager.shorten_contexts.assert_not_called()  # type: ignore[attr-defined]
    assert datapoints[0].context == LONG_CONTEXT
    assert any(
        "no question/instruction was available" in message
        for message in _warnings(caplog)
    )


def test_without_question_enabled_shortening_warns(caplog):
    datapoints = [_datapoint(SHORT_CONTEXT)]
    rapidata_config.upload.contextShortening = True
    manager = _manager(shortened=["shortened context"])

    with caplog.at_level(logging.INFO):
        manager._apply_context_shortening(datapoints, question=None)

    manager.shorten_contexts.assert_not_called()  # type: ignore[attr-defined]
    assert datapoints[0].context == SHORT_CONTEXT
    assert any(
        "contextShortening is enabled" in message for message in _warnings(caplog)
    )
