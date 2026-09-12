"""Tests for the OTLP default that keeps test traffic out of the production collector.

The suite drives the SDK with mocks, so its validation failures are
indistinguishable from customer errors once they reach `otlp-sdk.rapidata.ai`.
`tests/conftest.py` sets `RAPIDATA_DISABLE_OTLP=1`, but it only covers runs that
collect this repo's conftest — the pytest check covers every other pytest run.
"""

from __future__ import annotations

import pytest

from rapidata.rapidata_client.config.logging_config import (
    LoggingConfig,
    _default_enable_otlp,
    _running_under_pytest,
)


def test_pytest_is_detected_in_this_process():
    assert _running_under_pytest() is True


def test_disabled_under_pytest_without_the_env_var(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RAPIDATA_DISABLE_OTLP", raising=False)

    assert _default_enable_otlp() is False


@pytest.mark.parametrize("value", ["1", "true", "YES"])
def test_disabled_by_env_var(monkeypatch: pytest.MonkeyPatch, value: str):
    monkeypatch.setenv("RAPIDATA_DISABLE_OTLP", value)

    assert _default_enable_otlp() is False


def test_enabled_outside_pytest(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RAPIDATA_DISABLE_OTLP", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        "rapidata.rapidata_client.config.logging_config.sys.modules",
        {k: v for k, v in __import__("sys").modules.items() if k != "pytest"},
    )

    assert _default_enable_otlp() is True


def test_explicit_true_overrides_the_pytest_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RAPIDATA_DISABLE_OTLP", raising=False)

    assert LoggingConfig(enable_otlp=True).enable_otlp is True
