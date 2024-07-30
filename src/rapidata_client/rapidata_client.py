from src.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from src.rapidata_client.order.rapidata_order_configuration import (
    RapidataOrderConfiguration,
)
from src.service.order_service import OrderService


class RapidataClient:
    def __init__(self, api_key: str, endpoint="https://api.rapidata.ai"):
        self.order_service = OrderService(api_key, endpoint)

    def new_order(self, name: str, question: str, categories: list[str]) -> RapidataOrderBuilder:
        return RapidataOrderBuilder(
            order_service=self.order_service,
            name=name,
            question=question,
            categories=categories,
        )
