from src.rapidata_client.order.rapidata_order_configuration import RapidataOrderConfiguration
from src.service.order_service import OrderService


class RapidataOrder:

    def __init__(self, config: RapidataOrderConfiguration, order_service: OrderService):
        self.config = config
        self.rapidata_service = order_service
        self.order_id = None

    def submit(self):
        self.order_id, dataset_id = self.rapidata_service.create_order(self.config)
        self.rapidata_service.submit(self.order_id)

