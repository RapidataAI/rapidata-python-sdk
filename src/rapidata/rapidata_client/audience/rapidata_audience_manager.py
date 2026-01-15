from __future__ import annotations
from typing import TYPE_CHECKING
from rapidata.rapidata_client.config import tracer
from rapidata.rapidata_client.config import logger

if TYPE_CHECKING:
    from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience
    from rapidata.service.openapi_service import OpenAPIService
    from rapidata.rapidata_client.filter import RapidataFilter


class RapidataAudienceManager:
    """Handles everything regarding audiences from creation to retrieval.

    A manager for creating, retrieving, and searching for audiences.
    Audiences are groups of annotators that can be recruited based on example tasks and assigned jobs.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service

    def create_audience(
        self,
        name: str,
        filters: list[RapidataFilter] | None = None,
    ) -> RapidataAudience:
        """Create a new audience.

        Creates a new audience with the specified name and optional filters.

        Args:
            name (str): The name of the audience.
            filters (list[RapidataFilter], optional): The list of filters to apply to the audience. Defaults to None (no filters).

        Returns:
            RapidataAudience: The created audience instance.
        """
        with tracer.start_as_current_span("RapidataAudienceManager.create_audience"):
            from rapidata.rapidata_client.audience.rapidata_audience import (
                RapidataAudience,
            )
            from rapidata.api_client.models.create_audience_request import (
                CreateAudienceRequest,
            )

            logger.debug(f"Creating audience: {name}")
            if filters is None:
                filters = []
            response = self._openapi_service.audience_api.audience_post(
                create_audience_request=CreateAudienceRequest(
                    name=name,
                    filters=[filter._to_audience_model() for filter in filters],
                ),
            )
            return RapidataAudience(
                id=response.audience_id,
                name=name,
                filters=filters,
                openapi_service=self._openapi_service,
            )

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
            response = self._openapi_service.audience_api.audience_audience_id_get(
                audience_id=audience_id,
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
        self, name: str = "", amount: int = 10
    ) -> list[RapidataAudience]:
        """Find your audiences by name.

        Args:
            name (str, optional): Filter audiences by name (matching audiences will contain this string). Defaults to "" for any audience.
            amount (int, optional): The maximum number of audiences to return. Defaults to 10.

        Returns:
            list[RapidataAudience]: A list of RapidataAudience instances.
        """
        with tracer.start_as_current_span("RapidataAudienceManager.find_audiences"):
            from rapidata.rapidata_client.filter._backend_filter_mapper import (
                BackendFilterMapper,
            )
            from rapidata.api_client.models.page_info import PageInfo
            from rapidata.api_client.models.query_model import QueryModel
            from rapidata.api_client.models.root_filter import RootFilter
            from rapidata.api_client.models.filter import Filter
            from rapidata.api_client.models.filter_operator import FilterOperator
            from rapidata.api_client.models.sort_criterion import SortCriterion
            from rapidata.api_client.models.sort_direction import SortDirection
            from rapidata.rapidata_client.audience.rapidata_audience import (
                RapidataAudience,
            )

            logger.debug(f"Finding audiences: {name}, {amount}")
            response = self._openapi_service.audience_api.audiences_get(
                request=QueryModel(
                    page=PageInfo(index=1, size=amount),
                    filter=RootFilter(
                        filters=[
                            Filter(
                                field="Name",
                                operator=FilterOperator.CONTAINS,
                                value=name,
                            )
                        ]
                    ),
                    sortCriteria=[
                        SortCriterion(
                            direction=SortDirection.DESC, propertyName="CreatedAt"
                        )
                    ],
                )
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
