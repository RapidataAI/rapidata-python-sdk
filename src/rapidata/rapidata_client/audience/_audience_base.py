from __future__ import annotations

from typing import TYPE_CHECKING
from rapidata.rapidata_client.config import logger, managed_print, tracer

if TYPE_CHECKING:
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.filter import RapidataFilter
    from rapidata.rapidata_client.job.rapidata_job_definition import (
        RapidataJobDefinition,
    )
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob
    from rapidata.api_client.models.create_job_endpoint_cost_warning import (
        CreateJobEndpointCostWarning,
    )


class RapidataAudienceBase:
    """Shared surface for any kind of Rapidata audience.

    Both :class:`RapidataAudience` (dimension audience — has its own pool of qualified
    annotators) and :class:`RapidataFilteredAudience` (a filtered view on top of a
    dimension audience) inherit from this. Code that only needs to read the id, run a
    job, or list jobs should accept ``RapidataAudienceBase``; code that needs to add
    qualification examples or change recruiting must take ``RapidataAudience``.

    Attributes:
        id (str): The unique identifier of the audience.
        name (str): The name of the audience.
        filters (list[RapidataFilter]): The filters applied to the audience. For a
            dimension audience these are the recruitment filters; for a filtered
            audience they are the slice on top of the base audience.
    """

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

    @property
    def name(self) -> str:
        """The name of the audience."""
        return self._name

    @property
    def filters(self) -> list[RapidataFilter]:
        """The filters applied to the audience."""
        return self._filters

    def assign_job(self, job_definition: RapidataJobDefinition) -> RapidataJob:
        """Assign a job to this audience.

        Creates a new job instance from the job definition and assigns it to this audience.
        The job will be executed by the annotators in this audience.

        Args:
            job_definition (JobDefinition): The job definition to create and assign to the audience.

        Returns:
            RapidataJob: The created job instance.
        """
        with tracer.start_as_current_span(f"{type(self).__name__}.assign_job"):
            from rapidata.api_client.models.create_job_endpoint_input import (
                CreateJobEndpointInput,
            )
            from rapidata.rapidata_client.job.rapidata_job import RapidataJob
            from datetime import datetime

            logger.debug(f"Assigning job to audience: {self.id}")
            response = self._openapi_service.order.job_api.job_post(
                create_job_endpoint_input=CreateJobEndpointInput(
                    audienceId=self.id,
                    jobDefinitionId=job_definition.id,
                ),
            )
            job = RapidataJob(
                job_id=response.job_id,
                name=job_definition.name,
                audience_id=self.id,
                created_at=datetime.now(),
                definition_id=job_definition.id,
                openapi_service=self._openapi_service,
            )
            logger.info(f"Assigned job to audience: {self.id}")
            managed_print(
                f"Job '{job.name}' is now viewable under: {job.job_details_page}"
            )
            self._warn_if_cost_exceeds_balance(job, response.cost_warning)
            return job

    @staticmethod
    def _warn_if_cost_exceeds_balance(
        job: RapidataJob, cost_warning: CreateJobEndpointCostWarning | None
    ) -> None:
        """Surface the create response's optional cost warning via the SDK logger.

        The job is created and runs regardless — this is an advisory estimate that it
        may pause for funds before finishing, not an error.
        """
        if cost_warning is None:
            return
        logger.warning(
            "Job '%s' has an estimated cost of %.2f, but the account balance is %.2f — "
            "it will likely pause about %.2f short of finishing. The job was created and "
            "runs as far as the balance allows; top up the account to let it complete. "
            "This is an estimate.",
            job.name,
            cost_warning.estimated_cost,
            cost_warning.available_balance,
            cost_warning.shortfall,
        )

    def find_jobs(
        self, name: str = "", amount: int = 10, page: int = 1
    ) -> list[RapidataJob]:
        """Find jobs assigned to this audience.

        Args:
            name (str, optional): Filter jobs by name (matching jobs will contain this string). Defaults to "" for any job.
            amount (int, optional): The maximum number of jobs to return. Defaults to 10.
            page (int, optional): The page of jobs to return. Defaults to 1.

        Returns:
            list[RapidataJob]: A list of RapidataJob instances assigned to this audience.
        """
        with tracer.start_as_current_span(f"{type(self).__name__}.find_jobs"):
            from rapidata.rapidata_client.job.rapidata_job import RapidataJob
            from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
                AudienceAudienceIdJobsGetJobIdParameter,
            )

            response = self._openapi_service.order.job_api.jobs_get(
                page=page,
                page_size=amount,
                name=AudienceAudienceIdJobsGetJobIdParameter(contains=name),
                audience_id=AudienceAudienceIdJobsGetJobIdParameter(eq=self.id),
                sort=["-created_at"],
            )
            return [
                RapidataJob(
                    job_id=job.job_id,
                    name=job.name,
                    audience_id=job.audience_id,
                    created_at=job.created_at,
                    definition_id=job.job_definition_id,
                    openapi_service=self._openapi_service,
                    pipeline_id=job.pipeline_id,
                )
                for job in response.items
            ]

    def __str__(self) -> str:
        return f"{type(self).__name__}(id={self.id}, name={self._name}, filters={self._filters})"

    def __repr__(self) -> str:
        return self.__str__()
