"""``client.asset.upload`` uploads through the shared, cached uploader and returns a reference."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from rapidata.rapidata_client.asset.rapidata_asset_manager import RapidataAssetManager
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._single_flight_cache import SingleFlightCache
from rapidata.rapidata_client.datapoints.assets.uploaded_asset import UploadedAsset

MODULE = "rapidata.rapidata_client.asset.rapidata_asset_manager"


def _service() -> MagicMock:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    return openapi_service


def _response(file_name: str, warnings: list[str] | None = None) -> MagicMock:
    response = MagicMock()
    response.file_name = file_name
    response.warnings = warnings
    return response


def test_upload_url_returns_a_reference_and_reuses_the_cache() -> None:
    openapi_service = _service()
    asset_url_post = openapi_service.asset.asset_api.asset_url_post
    asset_url_post.return_value = _response("0b4a1f8e.png")
    manager = RapidataAssetManager(openapi_service)

    with patch.object(AssetUploader, "_url_cache", SingleFlightCache("url", {})):
        first = manager.upload("https://host/a.png")
        second = manager.upload("https://host/a.png")

    assert first == second == UploadedAsset("0b4a1f8e.png")
    asset_url_post.assert_called_once_with(url="https://host/a.png")


def test_upload_file_returns_a_reference(tmp_path: Path) -> None:
    image = tmp_path / "a.png"
    image.write_bytes(b"png")
    openapi_service = _service()
    openapi_service.asset.asset_api.asset_file_post.return_value = _response(
        "5c2d9e7f.png"
    )
    manager = RapidataAssetManager(openapi_service)

    with patch.object(
        AssetUploader,
        "_get_file_cache",
        return_value=SingleFlightCache("file", {}),
    ):
        uploaded = manager.upload(str(image))

    assert uploaded == UploadedAsset("5c2d9e7f.png")
    openapi_service.asset.asset_api.asset_file_post.assert_called_once_with(
        file=str(image)
    )


def test_upload_logs_backend_warnings() -> None:
    openapi_service = _service()
    openapi_service.asset.asset_api.asset_url_post.return_value = _response(
        "0b4a1f8e.mp4", warnings=["video longer than 25 seconds"]
    )
    manager = RapidataAssetManager(openapi_service)

    with (
        patch.object(AssetUploader, "_url_cache", SingleFlightCache("url", {})),
        patch(f"{MODULE}.logger") as logger,
    ):
        manager.upload("https://host/clip.mp4")

    logger.warning.assert_called_once()
    assert "video longer than 25 seconds" in str(logger.warning.call_args)
