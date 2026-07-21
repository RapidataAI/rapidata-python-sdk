"""Tests for the ingestion stage / origin HTTP status surfaced on FailedUpload.

Remote-URL ingestion failures come back two ways: as a RapidataError whose
problem+json body carries `stage` / `upstreamHttpStatus` extensions (sync
path), and as a failed batch-result item exposing `stage` / `upstream_http_status`
(batch path). Both must land on FailedUpload so callers can branch on the stage.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from rapidata.api_client.models.batch_upload_url_status import BatchUploadUrlStatus
from rapidata.rapidata_client.datapoints._batch_asset_uploader import BatchAssetUploader
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.exceptions.rapidata_error import RapidataError


def test_from_exception_extracts_stage_and_http_status():
    error = RapidataError(
        status_code=422,
        message="The remote asset could not be retrieved.",
        details={
            "title": "The remote asset could not be retrieved.",
            "status": 422,
            "traceId": "00-abc-01",
            "stage": "download",
            "upstreamHttpStatus": 403,
        },
    )

    failed = FailedUpload.from_exception("https://host/a.jpg", error)

    assert failed.stage == "download"
    assert failed.http_status == 403
    assert failed.trace_id == "00-abc-01"


def test_from_exception_without_extensions_leaves_stage_none():
    error = RapidataError(
        status_code=400,
        message="Bad request",
        details={"title": "Bad request", "status": 400},
    )

    failed = FailedUpload.from_exception("https://host/a.jpg", error)

    assert failed.stage is None
    assert failed.http_status is None


def test_from_exception_non_rapidata_error_has_no_stage():
    failed = FailedUpload.from_exception("./local.jpg", ValueError("boom"))

    assert failed.stage is None
    assert failed.http_status is None
    assert failed.error_message == "boom"


def test_batch_result_failure_carries_stage_and_http_status():
    openapi_service = MagicMock()
    openapi_service.environment = "rapidata.ai"

    failed_item = MagicMock()
    failed_item.url = "https://host/a.jpg"
    failed_item.status = BatchUploadUrlStatus.FAILED
    failed_item.error_message = "The remote asset could not be retrieved."
    failed_item.stage = "download"
    failed_item.upstream_http_status = 403

    result = MagicMock()
    result.items = [failed_item]
    openapi_service.asset.batch_upload_api.asset_batch_upload_batch_upload_id_get.return_value = (
        result
    )

    uploader = BatchAssetUploader(openapi_service)
    successful, failures = uploader._process_single_batch("batch-1", {})

    assert successful == []
    assert len(failures) == 1
    assert failures[0].stage == "download"
    assert failures[0].http_status == 403


def test_datapoint_failure_propagates_single_stage():
    from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset

    asset_failures = [
        FailedUpload(
            item="https://host/a.jpg",
            error_message="not found",
            error_type="BatchUploadFailed",
            stage="download",
            http_status=404,
        )
    ]

    failed = RapidataDataset._build_asset_failure_for_datapoint(
        MagicMock(), asset_failures
    )

    assert failed.stage == "download"
    assert failed.http_status == 404


def test_datapoint_failure_drops_conflicting_stages():
    from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset

    asset_failures = [
        FailedUpload(
            item="https://host/a.jpg",
            error_message="not found",
            error_type="BatchUploadFailed",
            stage="download",
            http_status=404,
        ),
        FailedUpload(
            item="https://host/b.jpg",
            error_message="bad type",
            error_type="BatchUploadFailed",
            stage="content_type",
            http_status=None,
        ),
    ]

    failed = RapidataDataset._build_asset_failure_for_datapoint(
        MagicMock(), asset_failures
    )

    # Two assets failed at different stages — no single stage to report.
    assert failed.stage is None
    assert failed.http_status == 404


def test_format_error_details_includes_stage_and_http_status():
    failed = FailedUpload(
        item="https://host/a.jpg",
        error_message="The remote asset could not be retrieved.",
        error_type="RapidataError",
        stage="download",
        http_status=403,
    )

    rendered = failed.format_error_details()

    assert "Stage: download" in rendered
    assert "HTTP Status: 403" in rendered
