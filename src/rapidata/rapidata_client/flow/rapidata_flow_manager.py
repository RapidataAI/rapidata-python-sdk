from rapidata.service.openapi_service import OpenAPIService


class RapidataFlowManager:
    """Handles everything regarding flows from creation to retrieval.

    A manager for creating, retrieving, and searching for flows.
    Flows are used to add small flow items that can be solved fast without the order creation overhead.
    """

    def __init__(self, openapi_service: OpenAPIService):
        self._openapi_service = openapi_service

    def create_flow(self, name: str, description: str):
        pass
        # return self._openapi_service.create_flow(name, description)
