import os
import shutil
import subprocess
from pathlib import Path

import pytest

TEST_FILE = Path(__file__).parent / "docs_js" / "analytics.test.js"


def test_docs_analytics_passes_journey_protocol_fixtures():
    node = shutil.which("node")
    if node is None:
        if os.environ.get("CI"):
            pytest.fail("node is required to test docs/js/analytics.js")
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, "--test", str(TEST_FILE)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
