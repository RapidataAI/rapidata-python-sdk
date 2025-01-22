from rapidata.service.openapi_service import OpenAPIService

class DemographicManager:
    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service
    
    def create_demographic_rapid(self):
        self._openapi_service.rapid_api.rapid_create_demographic_rapid_post()
        