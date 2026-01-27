from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.datapoints._datapoint_uploader import DatapointUploader
from rapidata.rapidata_client.datapoints._asset_upload_orchestrator import (
    AssetUploadOrchestrator,
)
from rapidata.rapidata_client.utils.threaded_uploader import ThreadedUploader
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload
from rapidata.rapidata_client.config import rapidata_config


class RapidataDataset:
    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.id = dataset_id
        self.openapi_service = openapi_service
        self.datapoint_uploader = DatapointUploader(openapi_service)
        self.asset_orchestrator = AssetUploadOrchestrator(openapi_service)

    def add_datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> tuple[list[Datapoint], list[FailedUpload[Datapoint]]]:
        """
        Upload datapoints in two steps:
        Step 1/2: Upload all assets (throws exception if fails)
        Step 2/2: Create datapoints (using cached assets)

        Args:
            datapoints: List of datapoints to upload

        Returns:
            tuple[list[Datapoint], list[FailedUpload[Datapoint]]]: Lists of successful uploads and failed uploads with error details

        Raises:
            AssetUploadException: If any asset uploads fail in Step 1/2
        """

        # STEP 1/2: Upload ALL assets
        # This will throw AssetUploadException if any uploads fail
        if rapidata_config.upload.enableBatchUpload:
            self.asset_orchestrator.upload_all_assets(datapoints)

        # STEP 2/2: Create datapoints (all assets already uploaded)
        def upload_single_datapoint(datapoint: Datapoint, index: int) -> None:
            self.datapoint_uploader.upload_datapoint(
                dataset_id=self.id,
                datapoint=datapoint,
                index=index,
            )

        uploader: ThreadedUploader[Datapoint] = ThreadedUploader(
            upload_fn=upload_single_datapoint,
            description="Step 2/2: Creating datapoints",
        )

        successful_uploads, failed_uploads = uploader.upload(datapoints)

        return successful_uploads, failed_uploads

    def __str__(self) -> str:
        return f"RapidataDataset(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
