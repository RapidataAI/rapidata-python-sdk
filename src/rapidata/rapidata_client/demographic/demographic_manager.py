from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.assets import MediaAsset
from rapidata.api_client.models.create_demographic_rapid_model import CreateDemographicRapidModel
from rapidata.api_client.models.classify_payload import ClassifyPayload


class DemographicManager:
    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
    
    def create_demographic_rapid(self, 
                                 instruction: str,
                                 answer_options: list[str],
                                 datapoint: str,
                                 key: str):
        
        media = MediaAsset(path=datapoint)
        model = CreateDemographicRapidModel(
            key=key,
            payload=ClassifyPayload(
                _t="ClassifyPayload",
                possibleCategories=answer_options,
                title=instruction
            )
        )
        self._openapi_service.rapid_api.rapid_create_demographic_rapid_post(model=model, file=[media.to_file()])
        