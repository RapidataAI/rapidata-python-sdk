"""Tests for the OTLP defaults that keep test traffic out of the production collector.

Test suites drive the SDK with mocks, so their validation failures are
indistinguishable from customer errors once they reach `otlp-sdk.rapidata.ai`.
`tests/conftest.py` sets `RAPIDATA_DISABLE_OTLP=1`, but it only covers runs that
collect this repo's conftest — the test-runner check covers every other run, and
the tracer re-checks it on first use because the config defaults are fixed at
import time, before a runner has necessarily imported its mocks.
"""

from __future__ import annotations

import sys
import unittest.mock

import pytest

from rapidata.rapidata_client.config.logging_config import (
    LoggingConfig,
    _default_enable_otlp,
    _running_under_test,
)
from rapidata.rapidata_client.config.tracer import RapidataTracer

MODULES = "rapidata.rapidata_client.config.logging_config.sys.modules"


def hide_the_test_runner(
    monkeypatch: pytest.MonkeyPatch, *, hide_mock: bool = True
) -> None:
    """Make the process look like ordinary customer usage rather than a test run."""
    hidden = {"pytest", "unittest.mock"} if hide_mock else {"pytest"}
    monkeypatch.delenv("RAPIDATA_DISABLE_OTLP", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        MODULES, {k: v for k, v in sys.modules.items() if k not in hidden}
    )


def test_pytest_is_detected_in_this_process():
    assert _running_under_test() is True


def test_disabled_under_pytest_without_the_env_var(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RAPIDATA_DISABLE_OTLP", raising=False)

    assert _default_enable_otlp() is False


@pytest.mark.parametrize("value", ["1", "true", "YES"])
def test_disabled_by_env_var(monkeypatch: pytest.MonkeyPatch, value: str):
    monkeypatch.setenv("RAPIDATA_DISABLE_OTLP", value)

    assert _default_enable_otlp() is False


def test_enabled_outside_a_test_runner(monkeypatch: pytest.MonkeyPatch):
    hide_the_test_runner(monkeypatch)

    assert _default_enable_otlp() is True


def test_mock_import_counts_as_a_test_runner(monkeypatch: pytest.MonkeyPatch):
    hide_the_test_runner(monkeypatch, hide_mock=False)

    assert sys.modules["unittest.mock"] is unittest.mock
    assert _running_under_test() is True


def test_explicit_true_overrides_the_test_runner_default(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("RAPIDATA_DISABLE_OTLP", raising=False)

    assert LoggingConfig(enable_otlp=True).enable_otlp is True


def test_tracer_skips_export_when_the_runner_is_detected_after_import(
    monkeypatch: pytest.MonkeyPatch,
):
    hide_the_test_runner(monkeypatch)
    tracer = RapidataTracer()
    tracer._update_tracer(LoggingConfig())
    assert tracer._enabled is True

    # The runner imports its mocks only now — after the config default was fixed.
    monkeypatch.setattr(MODULES, {**sys.modules, "unittest.mock": unittest.mock})
    tracer._ensure_initialized()

    assert tracer._enabled is False
    assert tracer._real_tracer is None


def test_tracer_still_exports_when_the_user_opted_in(monkeypatch: pytest.MonkeyPatch):
    hide_the_test_runner(monkeypatch, hide_mock=False)
    tracer = RapidataTracer()
    tracer._update_tracer(LoggingConfig(enable_otlp=True))

    tracer._ensure_initialized()

    assert tracer._enabled is True
    assert tracer._real_tracer is not None
