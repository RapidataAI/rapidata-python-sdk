from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from diskcache import Disk, FanoutCache

from rapidata.rapidata_client.config import rapidata_config
from rapidata.rapidata_client.config.upload_config import UploadConfig
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader


def _run_planted(marker: str) -> str:
    Path(marker).write_text("ran")
    return "planted.jpg"


class _Planted:
    def __init__(self, marker: Path) -> None:
        self.marker = str(marker)

    def __reduce__(self):
        return (_run_planted, (self.marker,))


@pytest.fixture
def disk_uploader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cache_dir = tmp_path / "upload_cache"
    monkeypatch.setattr(
        rapidata_config, "upload", UploadConfig(cacheLocation=cache_dir, cacheShards=4)
    )
    monkeypatch.setattr(AssetUploader, "_file_cache", None)
    monkeypatch.setattr(AssetUploader, "_file_cache_uses_disk", None)

    service = MagicMock()
    service.environment = "rapidata.ai"
    response = MagicMock()
    response.file_name = "uploaded.jpg"
    response.warnings = None
    service.asset.asset_api.asset_file_post.return_value = response

    uploader = AssetUploader(service)
    storage = uploader._get_file_cache().get_storage()
    assert isinstance(storage, FanoutCache)
    image = tmp_path / "cat.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    yield uploader, service, cache_dir, str(image)
    storage.close()


def test_planted_pickle_is_a_miss_and_never_runs(disk_uploader, tmp_path: Path):
    uploader, service, cache_dir, image = disk_uploader
    marker = tmp_path / "marker"
    with FanoutCache(cache_dir, shards=4, disk=Disk) as writer:
        writer.set(uploader.get_file_cache_key(image), _Planted(marker))

    assert uploader.upload_asset(image) == "uploaded.jpg"
    assert uploader.upload_asset(image) == "uploaded.jpg"

    assert not marker.exists()
    service.asset.asset_api.asset_file_post.assert_called_once()


def test_entries_written_by_default_disk_still_hit(disk_uploader):
    uploader, service, cache_dir, image = disk_uploader
    with FanoutCache(cache_dir, shards=4, disk=Disk) as writer:
        writer.set(uploader.get_file_cache_key(image), "cached.jpg")

    assert uploader.upload_asset(image) == "cached.jpg"
    service.asset.asset_api.asset_file_post.assert_not_called()
