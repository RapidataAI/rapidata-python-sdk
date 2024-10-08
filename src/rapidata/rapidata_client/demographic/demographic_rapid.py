from rapidata.service.openapi_service import OpenAPIService
from rapidata.api_client.models.create_demographic_rapid_model import CreateDemographicRapidModel
from rapidata.api_client.models.classify_payload import ClassifyPayload


class DemographicRapid:

    @staticmethod
    def create_demographic_rapid(key:str, question: str, options: list[str], image_path:str, openapi_service: OpenAPIService) -> str:
        model = CreateDemographicRapidModel(
            key=key,
            payload=ClassifyPayload(
                _t = "ClassifyPayload",
                title=question,
                possibleCategories=options
            )
        )
        response = openapi_service.rapid_api.rapid_create_demographic_rapid_post(
            model=model
        )
        print(response)
        return "todo" # wait for updated api
