from __future__ import annotations
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from .failed_upload import FailedUpload
from typing import TYPE_CHECKING, Optional
from collections import defaultdict

if TYPE_CHECKING:
    from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
    from rapidata.rapidata_client.job.rapidata_job_definition import (
        RapidataJobDefinition,
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
    ):
        self.dataset = dataset
        self.order = order
        self.job_definition = job_definition
        self._failed_uploads = failed_uploads
        super().__init__(str(self))

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
                if fu.trace_id:
                    lines.append(f"    {fu.item} [trace_id={fu.trace_id}],")
                else:
                    lines.append(f"    {fu.item},")
            lines.append("  ]")

        failed_upload_message = "\n".join(lines)
        if self.order:
            failed_upload_message += f"\n\nTo run the order without the failed datapoints, call: \n\trapidata_client.order.get_order_by_id('{self.order.id}').run()"
        if self.job_definition:
            failed_upload_message += f"\n\nTo run the job definition without the failed datapoints, call: \n\taudience.assign_job(rapidata_client.job.get_job_definition_by_id('{self.job_definition.id}'))"

        failed_upload_message += f"\n\nFor recovery strategies, see: https://docs.rapidata.ai/3.x/error_handling/"
        return failed_upload_message
