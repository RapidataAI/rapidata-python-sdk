from __future__ import annotations

from typing import TYPE_CHECKING
from rapidata.rapidata_client.audience.training_rapid_uploader import (
    TrainingRapidUploader,
)
from rapidata.rapidata_client.config import logger, tracer, rapidata_config

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.filter import RapidataFilter
    from rapidata.rapidata_client.validation.rapids.rapids import Rapid
    from rapidata.rapidata_client.job.job_definition import (
        JobDefinition,
    )
    from rapidata.rapidata_client.order.rapidata_order import RapidataOrder


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
        self._training_rapid_uploader = TrainingRapidUploader(openapi_service)

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

    # TODO: rename?
    def add_validation_rapids(self, rapids: list[Rapid]) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudience.add_validation_rapid"):
            logger.debug(f"Adding validation rapids: {rapids} to audience: {self.id}")
            self._training_rapid_uploader.upload_training_rapids_to_audience(
                rapids, self.id
            )

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
                    jobDefinitionId=job.id,
                ),
            )
            logger.info(f"Assigned job to audience: {self.id}")
            return self

    def __str__(self) -> str:
        return f"RapidataAudience(id={self.id}, name={self._name}, filters={self._filters})"

    def __repr__(self) -> str:
        return self.__str__()
