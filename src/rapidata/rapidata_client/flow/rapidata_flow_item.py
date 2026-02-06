from rapidata.service.openapi_service import OpenAPIService


class RapidataFlowItem:
    def __init__(self, id: str, name: str, openapi_service: OpenAPIService):
        self.id = id
        self.name = name
        self._openapi_service = openapi_service

    def get_results(self):
        pass
