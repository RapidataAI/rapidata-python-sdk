from typing import cast
from rapidata.api_client.models.file_asset_model import FileAssetModel
from rapidata.api_client.models.get_failed_datapoints_result import (
    GetFailedDatapointsResult,
)
from rapidata.api_client.models.multi_asset_model import MultiAssetModel
from rapidata.api_client.models.original_filename_metadata_model import (
    OriginalFilenameMetadataModel,
)
from rapidata.api_client.models.source_url_metadata_model import SourceUrlMetadataModel
from rapidata.rapidata_client.datapoints.assets import MediaAsset, MultiAsset
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.order.dataset._rapidata_dataset import RapidataDataset
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


class FailedUploadException(Exception):
    """Custom error class for Failed Uploads to the Rapidata order."""

    def __init__(
        self,
        dataset: RapidataDataset,
        order: RapidataOrder,
        failed_uploads: list[Datapoint],
    ):
        self.dataset = dataset
        self.order = order
        self.failed_uploads = failed_uploads

    def __str__(self) -> str:
        return f"Failed to upload {self.failed_uploads}"
