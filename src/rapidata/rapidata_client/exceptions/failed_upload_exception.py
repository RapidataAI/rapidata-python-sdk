from __future__ import annotations
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from .failed_upload import FailedUpload
from typing import TYPE_CHECKING, Optional
from collections import defaultdict

if TYPE_CHECKING:
    from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
    from rapidata.rapidata_client.job.job_definition import JobDefinition
    from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


class FailedUploadException(Exception):
    """Custom error class for Failed Uploads to the Rapidata order."""

    def __init__(
        self,
        dataset: RapidataDataset,
        failed_uploads: list[FailedUpload[Datapoint]],
        order: Optional[RapidataOrder] = None,
        job: Optional[JobDefinition] = None,
    ):
        self.dataset = dataset
        self.order = order
        self.job = job
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

        for reason, datapoints in self.failures_by_reason.items():
            lines.append(f"  '{reason}': [")
            for dp in datapoints:
                lines.append(f"    {dp},")
            lines.append("  ]")

        return "\n".join(lines)
