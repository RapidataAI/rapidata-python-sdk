from __future__ import annotations
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
    from rapidata.rapidata_client.job.job_definition import JobDefinition
    from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


class FailedUploadException(Exception):
    """Custom error class for Failed Uploads to the Rapidata order."""

    def __init__(
        self,
        dataset: RapidataDataset,
        failed_uploads: list[Datapoint],
        order: Optional[RapidataOrder] = None,
        job: Optional[JobDefinition] = None,
    ):
        self.dataset = dataset
        self.order = order
        self.job = job
        self.failed_uploads = failed_uploads

    def __str__(self) -> str:
        return f"Failed to upload {self.failed_uploads}"
