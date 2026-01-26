from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.datapoints._datapoint_uploader import DatapointUploader
from rapidata.rapidata_client.utils.threaded_uploader import ThreadedUploader
from rapidata.rapidata_client.exceptions.failed_upload import FailedUpload


class RapidataDataset:
    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.id = dataset_id
        self.openapi_service = openapi_service
        self.datapoint_uploader = DatapointUploader(openapi_service)

    def add_datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> tuple[list[Datapoint], list[FailedUpload[Datapoint]]]:
        """
        Process uploads in chunks with a ThreadPoolExecutor.

        Args:
            datapoints: List of datapoints to upload

        Returns:
            tuple[list[Datapoint], list[FailedUpload[Datapoint]]]: Lists of successful uploads and failed uploads with error details
        """

        def upload_single_datapoint(datapoint: Datapoint, index: int) -> None:
            self.datapoint_uploader.upload_datapoint(
                dataset_id=self.id,
                datapoint=datapoint,
                index=index,
            )

        uploader: ThreadedUploader[Datapoint] = ThreadedUploader(
            upload_fn=upload_single_datapoint,
            description="Uploading datapoints",
        )

        successful_uploads, failed_uploads = uploader.upload(datapoints)

        return successful_uploads, failed_uploads

    def __str__(self) -> str:
        return f"RapidataDataset(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
