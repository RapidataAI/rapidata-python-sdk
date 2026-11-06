"""Tests for the on-disk file-upload cache.

The cache folder maps each local file to the name the asset service gave it on
upload. An entry in that folder that would unpickle to anything else must be
treated as a miss, so the file is uploaded again and the entry's code never runs.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from diskcache_community import Disk, FanoutCache

from rapidata.rapidata_client.config import rapidata_config
from rapidata.rapidata_client.config.upload_config import UploadConfig
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader


def _plant(marker: str) -> str:
    Path(marker).write_text("ran")
    return "planted.jpg"


class _Planted:
    def __init__(self, marker: Path) -> None:
        self.marker = str(marker)

    def __reduce__(self):
        return (_plant, (self.marker,))


def test_planted_pickle_in_disk_cache_is_a_miss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_dir = tmp_path / "upload_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(
        rapidata_config, "upload", UploadConfig(cacheLocation=cache_dir, cacheShards=4)
    )
    monkeypatch.setattr(AssetUploader, "_file_cache", None)
    monkeypatch.setattr(AssetUploader, "_file_cache_uses_disk", None)

    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    response = MagicMock()
    response.file_name = "uploaded.jpg"
    response.warnings = None
    openapi_service.asset.asset_api.asset_file_post.return_value = response
    uploader = AssetUploader(openapi_service)
    storage = uploader._get_file_cache().get_storage()
    assert isinstance(storage, FanoutCache)

    image = tmp_path / "cat.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    marker = tmp_path / "marker"
    with FanoutCache(cache_dir, shards=4, disk=Disk) as other_writer:
        other_writer.set(uploader.get_file_cache_key(str(image)), _Planted(marker))

    try:
        assert uploader.upload_asset(str(image)) == "uploaded.jpg"
        assert uploader.upload_asset(str(image)) == "uploaded.jpg"
    finally:
        storage.close()

    assert not marker.exists()
    openapi_service.asset.asset_api.asset_file_post.assert_called_once()
