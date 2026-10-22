import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
TEST_FILE = ROOT / "tests" / "docs_js" / "analytics.test.js"


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


def test_consent_controls_are_excluded_from_autocapture():
    sources = [ROOT / "mkdocs.yml", ROOT / "site_root" / "developers" / "index.html"]
    controls = [
        tag
        for source in sources
        for tag in re.findall(r"<[^>]*data-rd-consent[^>]*>", source.read_text())
    ]
    assert len(controls) == len(sources)
    for tag in controls:
        classes = re.search(r'class="([^"]*)"', tag)
        assert classes and "ph-no-capture" in classes.group(1).split(), tag
