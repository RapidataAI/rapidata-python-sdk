from src.rapidata_client.order.rapidata_order_builder import RapidataOrderBuilder
from src.service.rapidata_api_services.rapidata_service import RapidataService


class RapidataClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str = "https://api.rapidata.ai",
    ):
        self._rapidata_service = RapidataService(
            client_id=client_id, client_secret=client_secret, endpoint=endpoint
        )

    def new_order(
        self, name: str, question: str, categories: list[str]
    ) -> RapidataOrderBuilder:
        return RapidataOrderBuilder(
            rapidata_service=self._rapidata_service,
            name=name,
            question=question,
            categories=categories,
        )
