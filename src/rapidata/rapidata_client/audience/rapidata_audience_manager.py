from rapidata.api_client.models.create_audience_request import CreateAudienceRequest
from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience
from rapidata.rapidata_client.validation.validation_set_manager import (
    ValidationSetManager,
)
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config import tracer


class RapidataAudienceManager:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service
        self._validation_set_manager = ValidationSetManager(openapi_service)

    def create_audience(
        self,
        name: str,
        filters: list[RapidataFilter] | None = None,
    ) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudienceManager.create_audience"):
            logger.debug(f"Creating audience: {name}")
            if filters is None:
                filters = []
            validation_set = self._validation_set_manager._create_validation_set(
                name=name + " Filtering Validation Set",
                dimensions=[],
            )
            response = self.openapi_service.audience_api.audience_post(
                create_audience_request=CreateAudienceRequest(
                    name=name,
                    validationSetId=validation_set.id,
                ),
            )
            validation_set.update_dimensions([response.audience_id])
            return RapidataAudience(
                id=response.audience_id,
                name=name,
                filters=filters,
                validation_set=validation_set,
                openapi_service=self.openapi_service,
            )

    def get_audience_by_id(self, audience_id: str) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudienceManager.get_audience_by_id"):
            logger.debug(f"Getting audience by id: {audience_id}")
            # will request the audience from the API as soon as endpoint is ready
            return RapidataAudience(
                id=audience_id,
                name="",
                filters=[],
                validation_set=None,
                openapi_service=self.openapi_service,
            )

    def find_audiences(
        self, name: str = "", amount: int = 10
    ) -> list[RapidataAudience]:
        with tracer.start_as_current_span("RapidataAudienceManager.find_audiences"):
            logger.debug(f"Finding audiences: {name}, {amount}")
            # will request the audiences from the API as soon as endpoint is ready
            return [
                RapidataAudience(
                    id=f"audience_{i}",
                    name=f"Audience {i}",
                    filters=[],
                    validation_set=None,
                    openapi_service=self.openapi_service,
                )
                for i in range(amount)
            ]

    def __str__(self) -> str:
        return "RapidataAudienceManager"

    def __repr__(self) -> str:
        return self.__str__()
