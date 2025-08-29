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


def _parse_failed_uploads(failed_uploads: GetFailedDatapointsResult) -> list[Datapoint]:
    failed_datapoints = failed_uploads.datapoints
    if not failed_datapoints:
        return []
    if isinstance(failed_datapoints[0].asset.actual_instance, FileAssetModel):
        failed_assets = [
            MediaAsset(
                __get_asset_name(cast(FileAssetModel, datapoint.asset.actual_instance))
            )
            for datapoint in failed_datapoints
        ]
    elif isinstance(failed_datapoints[0].asset.actual_instance, MultiAssetModel):
        failed_assets = []
        backend_assets = [
            cast(MultiAssetModel, failed_upload.asset.actual_instance).assets
            for failed_upload in failed_datapoints
        ]
        for assets in backend_assets:
            failed_assets.append(
                MultiAsset(
                    [
                        MediaAsset(
                            __get_asset_name(
                                cast(FileAssetModel, asset.actual_instance)
                            )
                        )
                        for asset in assets
                        if isinstance(asset.actual_instance, FileAssetModel)
                    ]
                )
            )
    else:
        raise ValueError(
            f"Unsupported asset type: {type(failed_datapoints[0].asset.actual_instance)}"
        )

    return [Datapoint(asset=asset) for asset in failed_assets]


def __get_asset_name(failed_datapoint: FileAssetModel) -> str:
    metadata = failed_datapoint.metadata
    if "sourceUrl" in metadata:
        return cast(SourceUrlMetadataModel, metadata["sourceUrl"].actual_instance).url
    elif "originalFilename" in metadata:
        return cast(
            OriginalFilenameMetadataModel, metadata["originalFilename"].actual_instance
        ).original_filename
    else:
        return ""
