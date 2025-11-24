from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config import tracer


class RapidataAudienceManager:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def create_audience(
        self,
        name: str,
        filters: list[RapidataFilter],
    ) -> RapidataAudience:
        with tracer.start_as_current_span("RapidataAudienceManager.create_audience"):
            logger.debug(f"Creating audience: {name}")
            # will request the audience from the API as soon as endpoint is ready
            return RapidataAudience(
                id=f"audience_{name}",
                name=name,
                filters=filters,
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
                    openapi_service=self.openapi_service,
                )
                for i in range(amount)
            ]

    def __str__(self) -> str:
        return "RapidataAudienceManager"

    def __repr__(self) -> str:
        return self.__str__()
