from __future__ import annotations

from rapidata.rapidata_client.exceptions.failed_upload_exception import (
    FailedUploadException,
)
from typing import Literal
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.config import tracer, logger, managed_print
import webbrowser
import urllib.parse
from colorama import Fore


class JobDefinition:
    def __init__(
        self,
        id: str,
        name: str,
        openapi_service: OpenAPIService,
    ):
        self._id = id
        self._name = name
        self._openapi_service = openapi_service
        self._job_details_page = (
            f"https://app.{self._openapi_service.environment}/definitions/{self._id}"
        )

    def preview(self) -> JobDefinition:
        """Will open the browser where you can preview the job definition before giving it to an audience."""
        logger.info("Opening order details page in browser...")
        if not webbrowser.open(self._job_details_page):
            encoded_url = urllib.parse.quote(
                self._job_details_page, safe="%/:=&?~#+!$,;'@()*[]"
            )
            managed_print(
                Fore.RED
                + f"Please open this URL in your browser: '{encoded_url}'"
                + Fore.RESET
            )
        return self

    def update_dataset(
        self,
        datapoints: list[str] | list[list[str]],
        data_type: Literal["text", "media"] = "media",
        contexts: list[str] | None = None,
        media_contexts: list[str] | None = None,
        sentences: list[str] | None = None,
        private_metadata: list[dict[str, str]] | None = None,
    ) -> JobDefinition:
        """Update the dataset of the job definition.

        Args:
            datapoints (list[str] | list[list[str]]): paths to the datapoints or strings for text datapoints.
            data_type (Literal["text", "media"]): The type of the datapoints.
        """
        with tracer.start_as_current_span("JobDefinition.update_dataset"):
            from rapidata.rapidata_client.datapoints._datapoints_validator import (
                DatapointsValidator,
            )
            from rapidata.api_client.models.create_dataset_endpoint_input import (
                CreateDatasetEndpointInput,
            )
            from rapidata.rapidata_client.dataset._rapidata_dataset import (
                RapidataDataset,
            )
            from rapidata.api_client.models.create_job_revision_endpoint_input import (
                CreateJobRevisionEndpointInput,
            )

            datapoints_list = DatapointsValidator.map_datapoints(
                datapoints=datapoints,
                contexts=contexts,
                media_contexts=media_contexts,
                sentences=sentences,
                private_metadata=private_metadata,
                data_type=data_type,
            )

            dataset = self._openapi_service.dataset_api.dataset_post(
                create_dataset_endpoint_input=CreateDatasetEndpointInput(
                    name=self._name + "_dataset"
                )
            )

            rapidata_dataset = RapidataDataset(
                dataset.dataset_id, self._openapi_service
            )

            with tracer.start_as_current_span("update_datapoints"):
                _, failed_uploads = rapidata_dataset.add_datapoints(datapoints_list)
                if failed_uploads:
                    raise FailedUploadException(
                        rapidata_dataset, failed_uploads, job=self
                    )

            self._openapi_service.job_api.job_definition_definition_id_revision_post(
                definition_id=self._id,
                create_job_revision_endpoint_input=CreateJobRevisionEndpointInput(
                    datasetId=rapidata_dataset.id,
                ),
            )

            return self

    def __str__(self) -> str:
        return f"JobDefinition(id={self._id}, name={self._name})"

    def __repr__(self) -> str:
        return self.__str__()
