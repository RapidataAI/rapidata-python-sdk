"""Pytest configuration shared by the whole test suite.

The SDK ships OTLP tracing on by default, and `rapidata_config` reads
`RAPIDATA_DISABLE_OTLP` once at import time. Without this, every test run
exports spans to the production collector: the suite drives the SDK with
`MagicMock` arguments, so the resulting validation failures land in prod
telemetry as real errors from `Rapidata.Python.SDK` and drown out genuine
customer failures.

Setting the env var before `rapidata` is imported is what actually disables
tracing; the explicit config assignment below is a safety net in case something
imported the package during collection first.
"""

import os

os.environ["RAPIDATA_DISABLE_OTLP"] = "1"

from rapidata.rapidata_client.config import rapidata_config  # noqa: E402

rapidata_config.logging.enable_otlp = False
