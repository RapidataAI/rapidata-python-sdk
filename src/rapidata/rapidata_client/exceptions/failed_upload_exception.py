from rapidata.rapidata_client.datapoints.datapoint import Datapoint
from rapidata.rapidata_client.order._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


class FailedUploadException(Exception):
    """Custom error class for Failed Uploads to the Rapidata order."""
    def __init__(
        self, 
        dataset: RapidataDataset,
        order: RapidataOrder,
        failed_uploads: list[Datapoint]
    ):
        self.dataset = dataset
        self.order = order
        self.failed_uploads = failed_uploads

    def __str__(self) -> str:
        return f"Failed to upload {self.failed_uploads}"
