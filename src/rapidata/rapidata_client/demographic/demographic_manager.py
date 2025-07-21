from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.datapoints.assets import MediaAsset
from rapidata.api_client.models.create_demographic_rapid_model import CreateDemographicRapidModel
from rapidata.api_client.models.classify_payload import ClassifyPayload
from rapidata.rapidata_client.logging import logger

class DemographicManager:
    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
        logger.debug("DemographicManager initialized")
    
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
        
        self._openapi_service.rapid_api.rapid_demographic_post(model=model, file=[media.to_file()])
        