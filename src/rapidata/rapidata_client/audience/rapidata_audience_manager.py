from __future__ import annotations
from typing import TYPE_CHECKING
from rapidata.rapidata_client.config import tracer
from rapidata.rapidata_client.config import logger

if TYPE_CHECKING:
    from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.filter import RapidataFilter
    from rapidata.api_client.models.i_graduation_rule import IGraduationRule


class RapidataAudienceManager:
    """Handles everything regarding audiences from creation to retrieval.

    A manager for creating, retrieving, and searching for audiences.
    Audiences are groups of annotators that can be recruited based on example tasks and assigned jobs.
    """

    # Defaults the backend applies when no graduation rule is sent. Mirrored
    # here because the TaskAccuracy wire variant requires both fields, so
    # supplying only one of target_accuracy / min_tasks means we still have to
    # send the other.
    _DEFAULT_TARGET_ACCURACY = 0.75
    _DEFAULT_MIN_TASKS = 10

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service

    def _build_task_accuracy_rule(
        self,
        target_accuracy: float | None,
        min_tasks: int | None,
        max_tasks: int | None,
    ) -> IGraduationRule | None:
        """Build a TaskAccuracy graduation rule, or None to let the server default.

        Returns None only when the caller opted out entirely (no knob set), so the
        backend applies its own default rule.
        """
        if target_accuracy is None and min_tasks is None and max_tasks is None:
            return None

        effective_accuracy = (
            target_accuracy
            if target_accuracy is not None
            else self._DEFAULT_TARGET_ACCURACY
        )
        effective_min_tasks = (
            min_tasks if min_tasks is not None else self._DEFAULT_MIN_TASKS
        )

        if not 0.0 <= effective_accuracy <= 1.0:
            raise ValueError(
                f"target_accuracy must be between 0.0 and 1.0, got {effective_accuracy}."
            )
        if effective_min_tasks < 1:
            raise ValueError(
                f"min_tasks must be at least 1, got {effective_min_tasks}."
            )
        if max_tasks is not None and max_tasks < effective_min_tasks:
            raise ValueError(
                f"max_tasks ({max_tasks}) must be greater than or equal to "
                f"min_tasks ({effective_min_tasks})."
            )

        from rapidata.api_client.models.i_graduation_rule import IGraduationRule
        from rapidata.api_client.models.i_graduation_rule_task_accuracy_rule import (
            IGraduationRuleTaskAccuracyRule,
        )

        return IGraduationRule(
            actual_instance=IGraduationRuleTaskAccuracyRule(
                _t="TaskAccuracy",
                targetAccuracy=effective_accuracy,
                minTasks=effective_min_tasks,
                maxTasks=max_tasks,
            )
        )

    def create_audience(
        self,
        name: str,
        filters: list[RapidataFilter] | None = None,
        target_accuracy: float | None = None,
        min_tasks: int | None = None,
        max_tasks: int | None = None,
    ) -> RapidataAudience:
        """Create a new audience.

        Creates a new audience with the specified name and optional filters.

        Annotators join an audience by passing a short admission trial: they must
        answer validation tasks well enough to be trusted. The two intuitive knobs
        below describe that bar as "solve N tasks at X accuracy":

        Args:
            name (str): The name of the audience.
            filters (list[RapidataFilter], optional): The list of filters to apply to the audience. Defaults to None (no filters).
            target_accuracy (float, optional): X — the fraction of validation tasks
                (0..1) an annotator must get right to be admitted. Defaults to None,
                in which case the server default of 0.75 applies.
            min_tasks (int, optional): N — the number of validation tasks an annotator
                must complete before the accuracy verdict is trusted. Defaults to None,
                in which case the server default of 10 applies.
            max_tasks (int, optional): Upper bound on admission-trial tasks before a
                verdict is forced. Defaults to None (no cap).

        Returns:
            RapidataAudience: The created audience instance.
        """
        with tracer.start_as_current_span("RapidataAudienceManager.create_audience"):
            from rapidata.rapidata_client.audience.rapidata_audience import (
                RapidataAudience,
            )
            from rapidata.api_client.models.create_audience_endpoint_input import (
                CreateAudienceEndpointInput,
            )

            logger.debug(f"Creating audience: {name}")
            if filters is None:
                filters = []

            graduation_rule = self._build_task_accuracy_rule(
                target_accuracy=target_accuracy,
                min_tasks=min_tasks,
                max_tasks=max_tasks,
            )
            response = self._openapi_service.audience.audience_api.audience_post(
                create_audience_endpoint_input=CreateAudienceEndpointInput(
                    name=name,
                    filters=[filter._to_audience_model() for filter in filters],
                    graduationRule=graduation_rule,
                ),
            )
            audience = RapidataAudience(
                id=response.audience_id,
                name=name,
                filters=filters,
                openapi_service=self._openapi_service,
            )
            return audience

    def get_audience_by_id(self, audience_id: str) -> RapidataAudience:
        """Get an audience by its ID.

        Args:
            audience_id (str): The unique identifier of the audience.

        Returns:
            RapidataAudience: The audience instance.
        """
        with tracer.start_as_current_span("RapidataAudienceManager.get_audience_by_id"):
            from rapidata.rapidata_client.filter._backend_filter_mapper import (
                BackendFilterMapper,
            )
            from rapidata.rapidata_client.audience.rapidata_audience import (
                RapidataAudience,
            )

            logger.debug(f"Getting audience by id: {audience_id}")
            response = (
                self._openapi_service.audience.audience_api.audience_audience_id_get(
                    audience_id=audience_id,
                )
            )
            return RapidataAudience(
                id=audience_id,
                name=response.name,
                filters=[
                    BackendFilterMapper.backend_filter_from_rapidata_filter(filter)
                    for filter in response.filters
                ],
                openapi_service=self._openapi_service,
            )

    def find_audiences(
        self, name: str = "", amount: int = 10, page: int = 1
    ) -> list[RapidataAudience]:
        """Find your audiences by name.

        Args:
            name (str, optional): Filter audiences by name (matching audiences will contain this string). Defaults to "" for any audience.
            amount (int, optional): The maximum number of audiences to return. Defaults to 10.
            page (int, optional): The page of audiences to return. Defaults to 1.

        Returns:
            list[RapidataAudience]: A list of RapidataAudience instances.
        """
        with tracer.start_as_current_span("RapidataAudienceManager.find_audiences"):
            from rapidata.rapidata_client.filter._backend_filter_mapper import (
                BackendFilterMapper,
            )
            from rapidata.api_client.models.audience_audience_id_jobs_get_job_id_parameter import (
                AudienceAudienceIdJobsGetJobIdParameter,
            )
            from rapidata.rapidata_client.audience.rapidata_audience import (
                RapidataAudience,
            )

            logger.debug(f"Finding audiences: {name}, {amount}")
            response = self._openapi_service.audience.audience_api.audiences_get(
                page=page,
                page_size=amount,
                name=AudienceAudienceIdJobsGetJobIdParameter(contains=name),
                sort=["-created_at"],
            )
            audiences = []
            for item in response.items:
                audiences.append(
                    RapidataAudience(
                        id=item.id,
                        name=item.name,
                        filters=[
                            BackendFilterMapper.backend_filter_from_rapidata_filter(
                                filter
                            )
                            for filter in item.filters
                        ],
                        openapi_service=self._openapi_service,
                    )
                )

            return audiences

    def __str__(self) -> str:
        return "RapidataAudienceManager"

    def __repr__(self) -> str:
        return self.__str__()
