from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from rapidata.rapidata_client.config import logger, tracer, rapidata_config
from rapidata.rapidata_client.audience.audience_example_handler import (
    AudienceExampleHandler,
)

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.filter import RapidataFilter
    from rapidata.rapidata_client.job.job_definition import (
        JobDefinition,
    )


class RapidataAudience:
    def __init__(
        self,
        id: str,
        name: str,
        filters: list[RapidataFilter],
        openapi_service: OpenAPIService,
    ):
        self.id = id
        self._name = name
        self._filters = filters
        self._openapi_service = openapi_service
        self._example_handler = AudienceExampleHandler(openapi_service, id)

    @property
    def name(self) -> str:
        return self._name

    @property
    def filters(self) -> list[RapidataFilter]:
        return self._filters

    def update_filters(self, filters: list[RapidataFilter]) -> RapidataAudience:
        # will update the filters for the audience as soon as endpoint is ready
        with tracer.start_as_current_span("RapidataAudience.update_filters"):
            from rapidata.api_client.models.update_audience_request import (
                UpdateAudienceRequest,
            )

            logger.debug(f"Updating filters for audience: {self.id} to {filters}")
            self._openapi_service.audience_api.audience_audience_id_patch(
                audience_id=self.id,
                update_audience_request=UpdateAudienceRequest(
                    filters=[filter._to_audience_model() for filter in filters],
                ),
            )
            self._filters = filters
            return self

    def update_name(self, name: str) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudience.update_name"):
            from rapidata.api_client.models.update_audience_request import (
                UpdateAudienceRequest,
            )

            logger.debug(f"Updating name for audience: {self.id} to {name}")
            self._openapi_service.audience_api.audience_audience_id_patch(
                audience_id=self.id,
                update_audience_request=UpdateAudienceRequest(name=name),
            )
            self._name = name
            return self

    def start_recruiting(self) -> RapidataAudience:
        # will start the recruiting for the audience as soon as endpoint is ready
        with tracer.start_as_current_span("RapidataAudience.start_recruiting"):
            logger.debug(f"Sending request to start recruiting for audience: {self.id}")
            self._openapi_service.audience_api.audience_audience_id_recruit_post(
                audience_id=self.id,
            )
            logger.info(f"Started recruiting for audience: {self.id}")
            return self

    def assign_job_to_audience(self, job: JobDefinition) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudience.assign_job_to_audience"):
            from rapidata.api_client.models.create_job_endpoint_input import (
                CreateJobEndpointInput,
            )

            logger.debug(f"Assigning job to audience: {self.id}")
            self._openapi_service.job_api.job_post(
                create_job_endpoint_input=CreateJobEndpointInput(
                    audienceId=self.id,
                    jobDefinitionId=job._id,
                ),
            )
            logger.info(f"Assigned job to audience: {self.id}")
            return self

    def add_classification_example(
        self,
        instruction: str,
        answer_options: list[str],
        datapoint: str,
        truth: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> RapidataAudience:
        with tracer.start_as_current_span(
            "RapidataAudience.add_classification_example"
        ):
            logger.debug(
                f"Adding classification example to audience: {self.id} with instruction: {instruction}, answer_options: {answer_options}, datapoint: {datapoint}, truths: {truth}, data_type: {data_type}, context: {context}, media_context: {media_context}, explanation: {explanation}"
            )
            self._example_handler.add_classification_example(
                instruction,
                answer_options,
                datapoint,
                truth,
                data_type,
                context,
                media_context,
                explanation,
            )
            return self

    def add_compare_example(
        self,
        instruction: str,
        truth: str,
        datapoint: list[str],
        data_type: Literal["media", "text"] = "media",
        context: str | None = None,
        media_context: str | None = None,
        explanation: str | None = None,
    ) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudience.add_compare_example"):
            logger.debug(
                f"Adding compare example to audience: {self.id} with instruction: {instruction}, truth: {truth}, datapoint: {datapoint}, data_type: {data_type}, context: {context}, media_context: {media_context}, explanation: {explanation}"
            )
            self._example_handler.add_compare_example(
                instruction,
                truth,
                datapoint,
                data_type,
                context,
                media_context,
                explanation,
            )
            return self

    def __str__(self) -> str:
        return f"RapidataAudience(id={self.id}, name={self._name}, filters={self._filters})"

    def __repr__(self) -> str:
        return self.__str__()
