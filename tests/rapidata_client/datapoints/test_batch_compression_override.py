"""The upload compression override must reach batched URL uploads.

`CompressionConfig(enabled=False)` preserves original media (image and video).
The batch path builds a `CompressionOverride` from the same global config the
single-upload path uses, so a benchmark set submitted in bulk keeps its
original resolution instead of silently ignoring the setting.
"""

from __future__ import annotations

import pytest

from rapidata import rapidata_config, CompressionConfig
from rapidata.rapidata_client.datapoints._batch_asset_uploader import BatchAssetUploader


@pytest.fixture(autouse=True)
def _reset_compression():
    original = rapidata_config.upload.compression
    yield
    rapidata_config.upload.compression = original


def test_no_config_sends_no_override():
    rapidata_config.upload.compression = None
    assert BatchAssetUploader._compression_override() is None


def test_unset_config_sends_no_override():
    rapidata_config.upload.compression = CompressionConfig()
    assert BatchAssetUploader._compression_override() is None


def test_disabled_compression_is_forwarded():
    rapidata_config.upload.compression = CompressionConfig(enabled=False)

    override = BatchAssetUploader._compression_override()

    assert override is not None
    assert override.to_dict() == {
        "enabled": False,
        "quality": None,
        "maxDimension": None,
    }


def test_all_fields_map_to_wire_names():
    rapidata_config.upload.compression = CompressionConfig(
        enabled=True, quality=70, max_dimension=1024
    )

    override = BatchAssetUploader._compression_override()

    assert override is not None
    # max_dimension maps to the wire alias maxDimension.
    assert override.to_dict() == {"enabled": True, "quality": 70, "maxDimension": 1024}
