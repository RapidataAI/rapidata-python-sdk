from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.datapoints._datapoint_uploader import DatapointUploader
from rapidata.rapidata_client.utils.threaded_uploader import ThreadedUploader


class RapidataDataset:
    def __init__(self, dataset_id: str, openapi_service: OpenAPIService):
        self.id = dataset_id
        self.openapi_service = openapi_service
        self.datapoint_uploader = DatapointUploader(openapi_service)

    def add_datapoints(
        self,
        datapoints: list[Datapoint],
    ) -> tuple[list[Datapoint], list[Datapoint]]:
        """
        Process uploads in chunks with a ThreadPoolExecutor.

        Args:
            datapoints: List of datapoints to upload

        Returns:
            tuple[list[Datapoint], list[Datapoint]]: Lists of successful and failed uploads
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

        if failed_uploads:
            logger.error(
                "Upload failed for %s datapoints: %s",
                len(failed_uploads),
                failed_uploads,
            )

        return successful_uploads, failed_uploads

    def __str__(self) -> str:
        return f"RapidataDataset(id={self.id})"

    def __repr__(self) -> str:
        return self.__str__()
