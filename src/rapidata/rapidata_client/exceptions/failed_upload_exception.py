from __future__ import annotations
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rapidata.rapidata_client.dataset._rapidata_dataset import RapidataDataset
    from rapidata.rapidata_client.job.job_definition import JobDefinition


class FailedUploadException(Exception):
    """Custom error class for Failed Uploads to the Rapidata order."""

    def __init__(
        self,
        dataset: RapidataDataset,
        job: JobDefinition,
        failed_uploads: list[Datapoint],
    ):
        self.dataset = dataset
        self.job = job
        self.failed_uploads = failed_uploads

    def __str__(self) -> str:
        return f"Failed to upload {self.failed_uploads}"
