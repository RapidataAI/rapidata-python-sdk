"""Tests for the gate that keeps test traffic out of the production collector.

Test suites drive SDK components directly with mocked services, so their
validation failures are indistinguishable from customer errors once they reach
`otlp-sdk.rapidata.ai`. Export therefore only starts once a RapidataClient has
been constructed; until then every span and log record stays local, whatever
the config default says.
"""

from __future__ import annotations

from importlib import import_module
from unittest.mock import MagicMock

import pytest

import rapidata.rapidata_client.rapidata_client as client_module
from rapidata.rapidata_client.config.logger import RapidataLogger
from rapidata.rapidata_client.config.logging_config import (
    LoggingConfig,
    _default_enable_otlp,
)
from rapidata.rapidata_client.config.tracer import NoOpSpan, RapidataTracer
from rapidata.rapidata_client.rapidata_client import RapidataClient

# The config package re-exports the `tracer` / `logger` instances under the
# module names, so the modules themselves have to be looked up explicitly.
tracer_module = import_module("rapidata.rapidata_client.config.tracer")
logger_module = import_module("rapidata.rapidata_client.config.logger")


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tracer_module, "OTLPSpanExporter", MagicMock())
    monkeypatch.setattr(logger_module, "OTLPLogExporter", MagicMock())


@pytest.mark.parametrize("value", ["1", "true", "YES"])
def test_default_disabled_by_env_var(monkeypatch: pytest.MonkeyPatch, value: str):
    monkeypatch.setenv("RAPIDATA_DISABLE_OTLP", value)

    assert _default_enable_otlp() is False


def test_default_enabled_without_the_env_var(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RAPIDATA_DISABLE_OTLP", raising=False)

    assert _default_enable_otlp() is True


def test_tracer_is_a_no_op_until_activated(no_network: None):
    tracer = RapidataTracer()
    tracer._update_tracer(LoggingConfig(enable_otlp=True))

    with tracer.start_as_current_span("RapidataAudience.add_locate_example") as span:
        assert isinstance(span, NoOpSpan)

    assert isinstance(tracer.start_span("x"), NoOpSpan)
    assert tracer._real_tracer is None


def test_tracer_exports_once_activated(no_network: None):
    tracer = RapidataTracer()
    tracer._update_tracer(LoggingConfig(enable_otlp=True))

    tracer.activate()
    with tracer.start_as_current_span("RapidataClient.__init__") as span:
        assert span.is_recording()

    assert tracer._real_tracer is not None


def test_activated_tracer_still_honours_enable_otlp_false(no_network: None):
    tracer = RapidataTracer()
    tracer._update_tracer(LoggingConfig(enable_otlp=False))

    tracer.activate()

    assert isinstance(tracer.start_span("x"), NoOpSpan)
    assert tracer._real_tracer is None


def test_logger_does_not_attach_otlp_until_activated(no_network: None):
    logger = RapidataLogger("rapidata-test-inactive")
    logger._update_logger(LoggingConfig(enable_otlp=True))

    logger.debug("driven by a mock")

    assert logger._otlp_handler is None
    assert logger._otlp_attached is False


def test_logger_attaches_otlp_once_activated(no_network: None):
    logger = RapidataLogger("rapidata-test-active")
    logger._update_logger(LoggingConfig(enable_otlp=True))

    logger.activate()
    logger.debug("from a real client")

    assert logger._otlp_handler is not None
    assert logger._otlp_handler in logger.handlers


def test_client_construction_activates_telemetry(monkeypatch: pytest.MonkeyPatch):
    activate = MagicMock()
    monkeypatch.setattr(client_module, "activate_telemetry", activate)
    monkeypatch.setattr(client_module, "OpenAPIService", MagicMock())
    monkeypatch.setattr(RapidataClient, "_check_version", lambda self: None)
    monkeypatch.setattr(RapidataClient, "_check_beta_features", lambda self: None)

    RapidataClient(client_id="id", client_secret="secret")

    activate.assert_called_once_with()
