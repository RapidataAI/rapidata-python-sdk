"""Tests for the job-definition creation state machine.

The machine must persist the remote job definition only once the datapoint
upload lands within the configured failure tolerance, and a failed run must be
resumable into the *same* dataset (no second dataset, no second definition).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.rapidata_client.job._job_creation_state_machine import (
    JobDefinitionCreationMachine,
)

MODULE = "rapidata.rapidata_client.job._job_creation_state_machine"
# _persist_definition imports this lazily; patch it so the mocked workflow/referee
# don't have to satisfy the pydantic input model.
JOB_INPUT = (
    "rapidata.api_client.models.create_job_definition_endpoint_input."
    "CreateJobDefinitionEndpointInput"
)


def _make_openapi_service() -> MagicMock:
    svc = MagicMock()
    svc.environment = "rapidata.ai"
    svc.dataset.dataset_api.dataset_post.return_value = MagicMock(dataset_id="ds-1")
    svc.order.job_api.job_definition_post.return_value = MagicMock(
        definition_id="def-1", pipeline_id="pipe-1"
    )
    return svc


def _failed(item) -> FailedUpload:
    return FailedUpload(item=item, error_message="boom", error_type="AssetUploadFailed")


def _run(svc, datapoints, tolerance, add_datapoints_side_effect):
    """Build and run a machine with a mocked dataset whose add_datapoints is scripted."""
    dataset = MagicMock()
    dataset.id = "ds-1"
    dataset.add_datapoints.side_effect = add_datapoints_side_effect

    machine = JobDefinitionCreationMachine(
        openapi_service=svc,
        name="My Job",
        workflow=MagicMock(),
        datapoints=datapoints,
        referee=MagicMock(),
        failure_tolerance=tolerance,
    )

    with (
        patch(f"{MODULE}.RapidataDataset", return_value=dataset),
        patch(f"{MODULE}.print_campaign_preview_qr_for_pipeline"),
        patch(f"{MODULE}.print_job_definition_preview_link"),
        patch(JOB_INPUT),
    ):
        return machine, dataset, machine.run()


def test_full_success_creates_definition():
    svc = _make_openapi_service()
    dps = ["a", "b", "c"]

    machine, dataset, job_def = _run(
        svc, dps, tolerance=0.0, add_datapoints_side_effect=[(dps, [])]
    )

    assert job_def.id == "def-1"
    svc.dataset.dataset_api.dataset_post.assert_called_once()
    svc.order.job_api.job_definition_post.assert_called_once()


def test_failure_within_tolerance_creates_definition():
    svc = _make_openapi_service()
    dps = [str(i) for i in range(100)]
    # 1/100 fails -> 1% == tolerance -> still creates the definition.
    result = ([str(i) for i in range(99)], [_failed("99")])

    _, _, job_def = _run(svc, dps, tolerance=0.01, add_datapoints_side_effect=[result])

    assert job_def.id == "def-1"
    svc.order.job_api.job_definition_post.assert_called_once()


def test_failure_exceeds_tolerance_raises_without_definition():
    svc = _make_openapi_service()
    dps = [str(i) for i in range(100)]
    # 5/100 fails, tolerance 0.0 -> no definition.
    result = ([str(i) for i in range(95)], [_failed(str(i)) for i in range(95, 100)])

    dataset = MagicMock()
    dataset.id = "ds-1"
    dataset.add_datapoints.side_effect = [result]
    machine = JobDefinitionCreationMachine(
        openapi_service=svc,
        name="My Job",
        workflow=MagicMock(),
        datapoints=dps,
        referee=MagicMock(),
        failure_tolerance=0.0,
    )

    with (
        patch(f"{MODULE}.RapidataDataset", return_value=dataset),
        patch(f"{MODULE}.print_campaign_preview_qr_for_pipeline"),
        patch(f"{MODULE}.print_job_definition_preview_link"),
        patch(JOB_INPUT),
    ):
        with pytest.raises(FailedUploadException) as excinfo:
            machine.run()

    exc = excinfo.value
    assert exc.machine is machine
    assert exc.job_definition is None
    svc.order.job_api.job_definition_post.assert_not_called()


def test_retry_reuses_dataset_and_persists_definition():
    svc = _make_openapi_service()
    dps = ["a", "b", "c", "d"]
    first = (["a", "b"], [_failed("c"), _failed("d")])  # 2/4 fail, tolerance 0.0
    second = (["c", "d"], [])  # retry uploads the failed two successfully

    dataset = MagicMock()
    dataset.id = "ds-1"
    dataset.add_datapoints.side_effect = [first, second]
    machine = JobDefinitionCreationMachine(
        openapi_service=svc,
        name="My Job",
        workflow=MagicMock(),
        datapoints=dps,
        referee=MagicMock(),
        failure_tolerance=0.0,
    )

    with (
        patch(f"{MODULE}.RapidataDataset", return_value=dataset) as dataset_cls,
        patch(f"{MODULE}.print_campaign_preview_qr_for_pipeline"),
        patch(f"{MODULE}.print_job_definition_preview_link"),
        patch(JOB_INPUT),
    ):
        with pytest.raises(FailedUploadException) as excinfo:
            machine.run()

        job_def = excinfo.value.retry()

    assert job_def.id == "def-1"
    # Only one dataset ever created, and only one definition persisted.
    dataset_cls.assert_called_once()
    svc.dataset.dataset_api.dataset_post.assert_called_once()
    svc.order.job_api.job_definition_post.assert_called_once()
    # Retry re-uploaded ONLY the failed datapoints, into the same dataset.
    assert dataset.add_datapoints.call_count == 2
    assert dataset.add_datapoints.call_args_list[1].args[0] == ["c", "d"]


def test_all_fail_never_creates_definition_even_at_full_tolerance():
    # Even failure_tolerance=1.0 must not create a definition over an empty
    # dataset: a job with zero datapoints has nothing to label.
    svc = _make_openapi_service()
    dps = ["a", "b", "c"]
    result = ([], [_failed("a"), _failed("b"), _failed("c")])

    dataset = MagicMock()
    dataset.id = "ds-1"
    dataset.add_datapoints.side_effect = [result]
    machine = JobDefinitionCreationMachine(
        openapi_service=svc,
        name="My Job",
        workflow=MagicMock(),
        datapoints=dps,
        referee=MagicMock(),
        failure_tolerance=1.0,
    )

    with (
        patch(f"{MODULE}.RapidataDataset", return_value=dataset),
        patch(f"{MODULE}.print_campaign_preview_qr_for_pipeline"),
        patch(f"{MODULE}.print_job_definition_preview_link"),
        patch(JOB_INPUT),
    ):
        with pytest.raises(FailedUploadException):
            machine.run()

    svc.order.job_api.job_definition_post.assert_not_called()
