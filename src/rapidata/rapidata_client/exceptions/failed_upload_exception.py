from __future__ import annotations
import errno
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from .failed_upload import FailedUpload
from typing import TYPE_CHECKING, Optional
from collections import defaultdict

if TYPE_CHECKING:
    from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
    from rapidata.rapidata_client.job.rapidata_job_definition import (
        RapidataJobDefinition,
    )
    from rapidata.rapidata_client.job._job_creation_state_machine import (
        JobDefinitionCreationMachine,
    )
    from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


class FailedUploadException(Exception):
    """Custom error class for Failed Uploads to the Rapidata order."""

    def __init__(
        self,
        dataset: RapidataDataset,
        failed_uploads: list[FailedUpload[Datapoint]],
        order: Optional[RapidataOrder] = None,
        job_definition: Optional[RapidataJobDefinition] = None,
        machine: Optional[JobDefinitionCreationMachine] = None,
    ):
        self.dataset = dataset
        self.order = order
        self.job_definition = job_definition
        self._failed_uploads = failed_uploads
        self._machine = machine
        super().__init__(str(self))

    def retry(self) -> RapidataJobDefinition:
        """Retry the failed datapoints and finish creating the job definition.

        Re-uploads only the datapoints that failed into the **same** dataset
        (never a new one), then creates the job definition once the upload is
        within the configured failure tolerance. Returns the created
        ``RapidataJobDefinition``. If some datapoints still fail beyond the
        tolerance, this raises ``FailedUploadException`` again (with the same
        dataset attached) so it can be caught and retried in a loop.

        This is the intended recovery path for a failed job-definition
        creation: fix whatever caused the failures (e.g. correct file paths),
        then call ``retry()`` - no need to re-specify the datapoints or drop
        down to ``dataset.add_datapoints`` manually.
        """
        if self._machine is None:
            raise RuntimeError(
                "retry() is only available for failed job-definition creation. "
                "To re-upload the failed datapoints manually, use "
                "dataset.add_datapoints(exception.failed_uploads)."
            )
        return self._machine.resume()

    @property
    def machine(self) -> Optional[JobDefinitionCreationMachine]:
        """The creation state machine backing ``retry()``, when this failure
        came from job-definition creation (``None`` for order uploads)."""
        return self._machine

    @property
    def failed_uploads(self) -> list[Datapoint]:
        """
        Get list of failed datapoints (backward compatibility).

        Returns:
            List of datapoints that failed to upload.
        """
        return [fu.item for fu in self._failed_uploads]

    @property
    def detailed_failures(self) -> list[FailedUpload[Datapoint]]:
        """
        Get detailed failure information including error messages.

        Returns:
            List of FailedUpload objects with item and error details.
        """
        return self._failed_uploads

    @property
    def failures_by_reason(self) -> dict[str, list[Datapoint]]:
        """
        Get failures grouped by error reason.

        Returns:
            Dictionary mapping error reasons to lists of failed datapoints.
        """
        grouped: dict[str, list[Datapoint]] = defaultdict(list)
        for failed_upload in self._failed_uploads:
            grouped[failed_upload.error_message].append(failed_upload.item)
        return dict(grouped)

    @property
    def failures_by_stage(self) -> dict[str, list[Datapoint]]:
        """
        Get failures grouped by ingestion stage (remote-URL assets).

        Only failures that carry a stage are included, so an empty dict means no
        failure reached the asset service with a classified stage (e.g. local
        file errors or datapoint-creation failures). The "internal" key is the
        only Rapidata-side fault; every other stage is caller-actionable.

        Returns:
            Dictionary mapping ingestion stage to lists of failed datapoints.
        """
        grouped: dict[str, list[Datapoint]] = defaultdict(list)
        for failed_upload in self._failed_uploads:
            if failed_upload.stage:
                grouped[failed_upload.stage].append(failed_upload.item)
        return dict(grouped)

    def _has_fd_exhaustion_failure(self) -> bool:
        """Whether any failure looks like the OS running out of file descriptors.

        Checks the errno first (EMFILE), falling back to the message text for
        cases where the OSError was wrapped or stringified before it reached us.
        """
        for fu in self._failed_uploads:
            exc = fu.exception
            if isinstance(exc, OSError) and exc.errno == errno.EMFILE:
                return True
            if "too many open files" in fu.error_message.lower():
                return True
        return False

    def __str__(self) -> str:
        total = len(self._failed_uploads)
        if total == 0:
            return "0 datapoints failed to upload"

        lines = [f"{total} datapoint(s) failed to upload:"]

        # Group internally on the full FailedUpload so each item can carry its
        # own trace ID (the public failures_by_reason groups by reason only and
        # discards that detail).
        grouped: dict[str, list[FailedUpload[Datapoint]]] = defaultdict(list)
        for fu in self._failed_uploads:
            grouped[fu.error_message].append(fu)

        for reason, failures in grouped.items():
            lines.append(f"  '{reason}': [")
            for fu in failures:
                annotations = []
                if fu.stage:
                    annotations.append(f"stage={fu.stage}")
                if fu.http_status is not None:
                    annotations.append(f"http_status={fu.http_status}")
                if fu.trace_id:
                    annotations.append(f"trace_id={fu.trace_id}")
                if annotations:
                    lines.append(f"    {fu.item} [{', '.join(annotations)}],")
                else:
                    lines.append(f"    {fu.item},")
            lines.append("  ]")

        failed_upload_message = "\n".join(lines)
        if self._has_fd_exhaustion_failure():
            failed_upload_message += (
                "\n\nThese failures look like file-descriptor exhaustion ('Too many open "
                "files'). The upload cache and worker pool each hold open file handles, so a "
                "large or concurrent upload can exceed a low 'ulimit -n'. To fix, either raise "
                "the OS limit (e.g. 'ulimit -n 8192') or lower the SDK's footprint via the "
                "'RAPIDATA_cacheShards' (default 32) and 'RAPIDATA_maxWorkers' (default 25) "
                "environment variables. See "
                "https://docs.rapidata.ai/3.x/config/#upload-configuration-options"
            )
        if self.machine is not None:
            failed_upload_message += (
                "\n\nNo job definition was created because the upload stayed outside the "
                "failure tolerance. Fix the failed datapoints and retry them into the same "
                "dataset (no new dataset is created) by catching this exception and calling: "
                "\n\tjob_definition = exception.retry()"
            )
        if self.order:
            failed_upload_message += f"\n\nTo run the order without the failed datapoints, call: \n\trapidata_client.order.get_order_by_id('{self.order.id}').run()"
        if self.job_definition:
            failed_upload_message += f"\n\nTo run the job definition without the failed datapoints, call: \n\taudience.assign_job(rapidata_client.job.get_job_definition_by_id('{self.job_definition.id}'))"

        failed_upload_message += f"\n\nFor recovery strategies, see: https://docs.rapidata.ai/3.x/error_handling/"
        return failed_upload_message
