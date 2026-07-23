"""Tests for surfacing non-fatal backend upload warnings.

The backend attaches advisory warnings (e.g. "video longer than 25 seconds")
to otherwise-successful uploads. They arrive two ways — on the sync file/URL
upload response, and per-item on a batch-upload result — and both must be
gathered and reported once via the SDK logger without failing the upload.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from rapidata.api_client.models.batch_upload_url_status import BatchUploadUrlStatus
from rapidata.rapidata_client.datapoints._asset_uploader import AssetUploader
from rapidata.rapidata_client.datapoints._asset_upload_orchestrator import (
    AssetUploadOrchestrator,
)
from rapidata.rapidata_client.datapoints._batch_asset_uploader import BatchAssetUploader
from rapidata.rapidata_client.datapoints._single_flight_cache import SingleFlightCache
from rapidata.rapidata_client.exceptions.asset_warning import AssetWarning

VIDEO_WARNING = (
    "Annotators can't solve tasks with videos longer than 25 seconds. If this is "
    "your use case, please reach out to info@rapidata.ai for a custom setup."
)


def _service() -> MagicMock:
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"
    return openapi_service


def test_file_upload_records_response_warnings():
    openapi_service = _service()
    response = MagicMock()
    response.file_name = "uploaded.mp4"
    response.warnings = [VIDEO_WARNING]
    openapi_service.asset.asset_api.asset_file_post.return_value = response

    uploader = AssetUploader(openapi_service)
    fresh_cache = SingleFlightCache("test file cache", storage={})
    with (
        patch.object(AssetUploader, "_build_file_cache_key", return_value="key"),
        patch.object(uploader, "_get_file_cache", return_value=fresh_cache),
    ):
        uploader._upload_file_asset("/tmp/clip.mp4")

    drained = uploader.drain_warnings()
    assert drained == [AssetWarning(item="/tmp/clip.mp4", message=VIDEO_WARNING)]
    # Draining clears the buffer.
    assert uploader.drain_warnings() == []


def test_url_upload_without_warnings_records_nothing():
    openapi_service = _service()
    response = MagicMock()
    response.file_name = "uploaded.jpg"
    response.warnings = None
    openapi_service.asset.asset_api.asset_url_post.return_value = response

    uploader = AssetUploader(openapi_service)
    with patch.object(
        uploader, "_url_cache", SingleFlightCache("test url cache", storage={})
    ):
        uploader._upload_url_asset("https://host/a.jpg")

    assert uploader.drain_warnings() == []


def test_batch_item_warnings_are_recorded():
    openapi_service = _service()

    completed_item = MagicMock()
    completed_item.url = "https://host/clip.mp4"
    completed_item.status = BatchUploadUrlStatus.COMPLETED
    completed_item.file_name = "uploaded.mp4"
    completed_item.warnings = [VIDEO_WARNING]

    result = MagicMock()
    result.items = [completed_item]
    openapi_service.asset.batch_upload_api.asset_batch_upload_batch_upload_id_get.return_value = (
        result
    )

    uploader = BatchAssetUploader(openapi_service)
    successful, failures = uploader._process_single_batch("batch-1", {})

    assert successful == ["https://host/clip.mp4"]
    assert failures == []
    assert uploader.drain_warnings() == [
        AssetWarning(item="https://host/clip.mp4", message=VIDEO_WARNING)
    ]


def test_orchestrator_surfaces_warnings_via_logger():
    orchestrator = AssetUploadOrchestrator(_service())
    orchestrator.asset_uploader.drain_warnings = MagicMock(  # type: ignore[method-assign]
        return_value=[AssetWarning(item="/tmp/clip.mp4", message=VIDEO_WARNING)]
    )
    orchestrator.batch_uploader.drain_warnings = MagicMock(  # type: ignore[method-assign]
        return_value=[AssetWarning(item="https://host/clip.mp4", message=VIDEO_WARNING)]
    )

    module = "rapidata.rapidata_client.datapoints._asset_upload_orchestrator"
    with patch(f"{module}.logger") as logger:
        orchestrator._log_upload_warnings(orchestrator._collect_warnings())

    assert logger.warning.call_count == 2
    logged = " ".join(str(c) for c in logger.warning.call_args_list)
    assert "/tmp/clip.mp4" in logged
    assert "https://host/clip.mp4" in logged
    assert VIDEO_WARNING in logged


def test_orchestrator_deduplicates_warnings_per_asset():
    orchestrator = AssetUploadOrchestrator(_service())
    duplicate = AssetWarning(item="/tmp/clip.mp4", message=VIDEO_WARNING)
    orchestrator.asset_uploader.drain_warnings = MagicMock(  # type: ignore[method-assign]
        return_value=[duplicate, duplicate]
    )
    orchestrator.batch_uploader.drain_warnings = MagicMock(  # type: ignore[method-assign]
        return_value=[]
    )

    collected = orchestrator._collect_warnings()

    assert collected == [duplicate]
