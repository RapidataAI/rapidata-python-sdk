"""Pytest configuration shared by the whole test suite.

OTLP export only starts once a `RapidataClient` is constructed, so tests that
drive components with `MagicMock` services never reach the collector. Disabling
it here as well keeps a test that does build a client from exporting either.
"""

import os

os.environ["RAPIDATA_DISABLE_OTLP"] = "1"

from rapidata.rapidata_client.config import rapidata_config  # noqa: E402

rapidata_config.logging.enable_otlp = False
