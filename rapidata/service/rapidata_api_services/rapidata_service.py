from rapidata.service.rapidata_api_services.base_service import BaseRapidataAPIService
from rapidata.service.rapidata_api_services.dataset_service import DatasetService
from rapidata.service.rapidata_api_services.order_service import OrderService


class RapidataService(BaseRapidataAPIService):
    def __init__(self, client_id: str, client_secret: str, endpoint: str):
        super().__init__(client_id, client_secret, endpoint)
        self._order_service = OrderService(client_id, client_secret, endpoint)
        self._dataset_service = DatasetService(client_id, client_secret, endpoint)

    @property
    def order(self):
        return self._order_service

    @property
    def dataset(self):
        return self._dataset_service
