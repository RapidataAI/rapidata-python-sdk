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
    from rapidata.rapidata_client.job.rapidata_job import RapidataJob


class RapidataAudience:
    """Represents a Rapidata audience.

    An audience is a group of annotators that can be recruited based on example tasks and assigned jobs.

    Attributes:
        id (str): The unique identifier of the audience.
        name (str): The name of the audience.
        filters (list[RapidataFilter]): The list of filters applied to the audience.
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
        self._example_handler = AudienceExampleHandler(openapi_service, id)

    @property
    def name(self) -> str:
        """The name of the audience."""
        return self._name

    @property
    def filters(self) -> list[RapidataFilter]:
        """The list of filters applied to the audience."""
        return self._filters

    def update_filters(self, filters: list[RapidataFilter]) -> RapidataAudience:
        """Update the filters for this audience.

        Args:
            filters (list[RapidataFilter]): The new list of filters to apply to the audience.

        Returns:
            RapidataAudience: The updated audience instance (self) for method chaining.
        """
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
        """Update the name of this audience.

        Args:
            name (str): The new name for the audience.

        Returns:
            RapidataAudience: The updated audience instance (self) for method chaining.
        """
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
        """Start recruiting annotators for this audience.

        This will begin the process of onboarding annotators for this audience.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
        with tracer.start_as_current_span("RapidataAudience.start_recruiting"):
            logger.debug(f"Sending request to start recruiting for audience: {self.id}")
            self._openapi_service.audience_api.audience_audience_id_recruit_post(
                audience_id=self.id,
            )
            logger.info(f"Started recruiting for audience: {self.id}")
            return self

    def assign_job(self, job_definition: JobDefinition) -> RapidataJob:
        """Assign a job to this audience.

        Creates a new job instance from the job definition and assigns it to this audience.
        The job will be executed by the annotators in this audience.

        Args:
            job_definition (JobDefinition): The job definition to create and assign to the audience.

        Returns:
            RapidataJob: The created job instance.
        """
        with tracer.start_as_current_span("RapidataAudience.assign_job"):
            from rapidata.api_client.models.create_job_endpoint_input import (
                CreateJobEndpointInput,
            )
            from rapidata.rapidata_client.job.rapidata_job import RapidataJob
            from datetime import datetime

            logger.debug(f"Assigning job to audience: {self.id}")
            response = self._openapi_service.job_api.job_post(
                create_job_endpoint_input=CreateJobEndpointInput(
                    audienceId=self.id,
                    jobDefinitionId=job_definition._id,
                ),
            )
            job = RapidataJob(
                job_id=response.job_id,
                name=job_definition._name,
                audience_id=self.id,
                created_at=datetime.now(),
                definition_id=job_definition._id,
                openapi_service=self._openapi_service,
            )
            logger.info(f"Assigned job to audience: {self.id}")
            return job

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
        """Add a classification training example to this audience.

        Training examples help annotators understand the task by showing them
        a sample datapoint with the correct answer before they start labeling.

        Args:
            instruction (str): The instruction for how the data should be classified.
            answer_options (list[str]): The list of possible answer options for the classification.
            datapoint (str): The datapoint (URL or path) to use as the training example.
            truth (list[str]): The correct answer(s) for this training example.
            data_type (Literal["media", "text"], optional): The data type of the datapoint. Defaults to "media".
            context (str, optional): Additional text context to display with the example. Defaults to None.
            media_context (str, optional): Additional media (URL or path) to display with the example. Defaults to None.
            explanation (str, optional): An explanation of why the truth is correct. Defaults to None.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
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
        """Add a comparison training example to this audience.

        Training examples help annotators understand the task by showing them
        a sample comparison with the correct answer before they start labeling.

        Args:
            instruction (str): The instruction for the comparison task.
            truth (str): The correct answer for this training example (which option should be selected).
            datapoint (list[str]): A list of exactly two datapoints (URLs or paths) to compare.
            data_type (Literal["media", "text"], optional): The data type of the datapoints. Defaults to "media".
            context (str, optional): Additional text context to display with the example. Defaults to None.
            media_context (str, optional): Additional media (URL or path) to display with the example. Defaults to None.
            explanation (str, optional): An explanation of why the truth is correct. Defaults to None.

        Returns:
            RapidataAudience: The audience instance (self) for method chaining.
        """
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

    def find_jobs(self, name: str = "", amount: int = 10) -> list[RapidataJob]:
        """Find jobs assigned to this audience.

        Args:
            name (str, optional): Filter jobs by name (matching jobs will contain this string). Defaults to "" for any job.
            amount (int, optional): The maximum number of jobs to return. Defaults to 10.

        Returns:
            list[RapidataJob]: A list of RapidataJob instances assigned to this audience.
        """
        with tracer.start_as_current_span("RapidataAudience.find_jobs"):
            from rapidata.rapidata_client.job.rapidata_job import RapidataJob
            from rapidata.api_client.models.query_model import QueryModel
            from rapidata.api_client.models.root_filter import RootFilter
            from rapidata.api_client.models.filter import Filter
            from rapidata.api_client.models.filter_operator import FilterOperator
            from rapidata.api_client.models.page_info import PageInfo
            from rapidata.api_client.models.sort_criterion import SortCriterion
            from rapidata.api_client.models.sort_direction import SortDirection

            response = self._openapi_service.job_api.jobs_get(
                request=QueryModel(
                    page=PageInfo(index=1, size=amount),
                    filter=RootFilter(
                        filters=[
                            Filter(
                                field="AudienceId",
                                operator=FilterOperator.EQ,
                                value=self.id,
                            ),
                            Filter(
                                field="Name",
                                operator=FilterOperator.CONTAINS,
                                value=name,
                            ),
                        ]
                    ),
                    sortCriteria=[
                        SortCriterion(
                            direction=SortDirection.DESC, propertyName="CreatedAt"
                        )
                    ],
                ),
            )
            return [
                RapidataJob(
                    job_id=job.job_id,
                    name=job.name,
                    audience_id=job.audience_id,
                    created_at=job.created_at,
                    definition_id=job.definition_id,
                    openapi_service=self._openapi_service,
                    pipeline_id=job.pipeline_id,
                )
                for job in response.items
            ]

    def __str__(self) -> str:
        return f"RapidataAudience(id={self.id}, name={self._name}, filters={self._filters})"

    def __repr__(self) -> str:
        return self.__str__()
