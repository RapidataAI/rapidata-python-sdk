from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Sequence

from rapidata.rapidata_client.config import logger, tracer
from rapidata.rapidata_client.config._qr_preview import (
    print_campaign_preview_qr_for_pipeline,
    print_job_definition_preview_link,
)
from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from rapidata.rapidata_client.job.rapidata_job_definition import RapidataJobDefinition

if TYPE_CHECKING:
    from rapidata.api_client.models.feature_flag import FeatureFlag
    from rapidata.rapidata_client.datapoints._datapoint import Datapoint
    from rapidata.rapidata_client.referee._base_referee import Referee
    from rapidata.rapidata_client.workflow import Workflow
    from rapidata.service.openapi_service import OpenAPIService


class _State(Enum):
    CREATE_DATASET = auto()
    UPLOAD_DATAPOINTS = auto()
    PERSIST_DEFINITION = auto()
    SUCCEEDED = auto()
    FAILED = auto()


class JobDefinitionCreationMachine:
    """Drives job-definition creation as an explicit state machine.

    The remote job definition is persisted only once the datapoint upload has
    landed within the configured failure tolerance, so a partially-uploaded
    dataset never leaves behind an incomplete definition. The machine keeps all
    intermediate state (the dataset, the datapoints still pending, the upload
    failures) so a failed run can be resumed via :meth:`resume` — re-uploading
    only the datapoints that failed into the *same* dataset rather than starting
    a fresh one. This is what backs ``FailedUploadException.retry()``.

    ``failure_tolerance`` is the fraction of the job's datapoints allowed to fail
    while still creating the definition (``0.0`` = strict, ``1.0`` = create
    regardless). The ratio is always measured against the original datapoint
    count, so it stays meaningful across resume attempts. Regardless of the
    tolerance, at least one datapoint must upload successfully - a definition
    over an empty dataset is never created.
    """

    def __init__(
        self,
        openapi_service: OpenAPIService,
        name: str,
        workflow: Workflow,
        datapoints: list[Datapoint],
        referee: Referee,
        failure_tolerance: float,
        rapid_feature_flags: Sequence[FeatureFlag] | None = None,
        campaign_feature_flags: Sequence[FeatureFlag] | None = None,
    ):
        self._openapi_service = openapi_service
        self._name = name
        self._workflow = workflow
        self._referee = referee
        self._failure_tolerance = failure_tolerance
        self._rapid_feature_flags = rapid_feature_flags
        self._campaign_feature_flags = campaign_feature_flags

        self._total_datapoints = len(datapoints)
        self._pending: list[Datapoint] = list(datapoints)
        self._succeeded_count = 0

        self._state = _State.CREATE_DATASET
        self.dataset: RapidataDataset | None = None
        self.failed_uploads: list[FailedUpload[Datapoint]] = []
        self.job_definition: RapidataJobDefinition | None = None

    def run(self) -> RapidataJobDefinition:
        """Drive the machine to a terminal state.

        Returns the created definition on success, or raises
        ``FailedUploadException`` (with this machine attached, so the caller can
        ``retry()``) when the upload stays outside the failure tolerance.
        """
        while self._state not in (_State.SUCCEEDED, _State.FAILED):
            if self._state is _State.CREATE_DATASET:
                self._create_dataset()
            elif self._state is _State.UPLOAD_DATAPOINTS:
                self._upload_datapoints()
            elif self._state is _State.PERSIST_DEFINITION:
                self._persist_definition()

        if self._state is _State.FAILED:
            # FAILED is only ever entered from _upload_datapoints, which runs
            # after the dataset exists.
            assert self.dataset is not None
            raise FailedUploadException(
                self.dataset,
                self.failed_uploads,
                job_definition=None,
                machine=self,
            )

        assert self.job_definition is not None
        return self.job_definition

    def resume(self) -> RapidataJobDefinition:
        """Retry a failed run, reusing the existing dataset.

        Only the datapoints that previously failed are re-uploaded (into the
        same dataset), then the machine re-evaluates the failure tolerance and
        persists the definition if it now fits.
        """
        # resume() is only reached via a raised FailedUploadException, which is
        # only produced once the dataset exists.
        assert self.dataset is not None
        self._pending = [fu.item for fu in self.failed_uploads]
        self.failed_uploads = []
        self._state = _State.UPLOAD_DATAPOINTS
        return self.run()

    def _create_dataset(self) -> None:
        from rapidata.api_client.models.create_dataset_endpoint_input import (
            CreateDatasetEndpointInput,
        )

        dataset = self._openapi_service.dataset.dataset_api.dataset_post(
            create_dataset_endpoint_input=CreateDatasetEndpointInput(
                name=self._name + "_dataset"
            )
        )
        self.dataset = RapidataDataset(dataset.dataset_id, self._openapi_service)
        self._state = _State.UPLOAD_DATAPOINTS

    def _upload_datapoints(self) -> None:
        assert self.dataset is not None
        with tracer.start_as_current_span("add_datapoints"):
            successful, failed = self.dataset.add_datapoints(self._pending)

        self._succeeded_count += len(successful)
        self.failed_uploads = failed
        self._pending = []

        failed_count = self._total_datapoints - self._succeeded_count
        failure_ratio = (
            failed_count / self._total_datapoints if self._total_datapoints else 0.0
        )

        # At least one datapoint must land regardless of the tolerance: a
        # definition over an empty dataset has nothing to label and would be
        # exactly the kind of useless remote artifact this machine prevents.
        within_tolerance = failure_ratio <= self._failure_tolerance
        if within_tolerance and self._succeeded_count > 0:
            if failed_count > 0:
                logger.warning(
                    "%d/%d datapoint(s) failed to upload (%.2f%%), which is within the "
                    "failure tolerance of %.2f%% - creating the job definition without them.",
                    failed_count,
                    self._total_datapoints,
                    failure_ratio * 100,
                    self._failure_tolerance * 100,
                )
            self._state = _State.PERSIST_DEFINITION
        else:
            self._state = _State.FAILED

    def _persist_definition(self) -> None:
        assert self.dataset is not None
        from rapidata.api_client.models.create_job_definition_endpoint_input import (
            CreateJobDefinitionEndpointInput,
        )

        response = self._openapi_service.order.job_api.job_definition_post(
            create_job_definition_endpoint_input=CreateJobDefinitionEndpointInput(
                definitionName=self._name,
                workflow=self._workflow._to_model(),
                datasetId=self.dataset.id,
                referee=self._referee._to_model(),
                rapidFeatureFlags=(
                    list(self._rapid_feature_flags)
                    if self._rapid_feature_flags
                    else None
                ),
                campaignFeatureFlags=(
                    list(self._campaign_feature_flags)
                    if self._campaign_feature_flags
                    else None
                ),
            )
        )
        self.job_definition = RapidataJobDefinition(
            id=response.definition_id,
            name=self._name,
            openapi_service=self._openapi_service,
        )

        print_campaign_preview_qr_for_pipeline(
            openapi_service=self._openapi_service,
            pipeline_id=response.pipeline_id,
        )
        print_job_definition_preview_link(
            environment=self._openapi_service.environment,
            job_definition_id=self.job_definition.id,
        )
        self._state = _State.SUCCEEDED
