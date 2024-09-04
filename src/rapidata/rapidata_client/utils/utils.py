from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.api_client.models.create_demographic_rapid_model import (
    CreateDemographicRapidModel,
)
from rapidata.service.openapi_service import OpenAPIService


class Utils:
    def __init__(self, openapi_service: OpenAPIService):
        self.openapi_service = openapi_service

    def new_demographic_rapid(
        self, question: str, options: list[str], identifier: str, media_path: str
    ):
        payload = ClassifyPayload(
            _t="ClassifyPayload", title=question, possibleCategories=options
        )
        model = CreateDemographicRapidModel(identifier=identifier, payload=payload)

        self.openapi_service.rapid_api.rapid_create_demographic_rapid_post(
            model=model, file=[media_path]
        )
