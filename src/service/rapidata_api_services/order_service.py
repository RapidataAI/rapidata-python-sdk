from src.rapidata_client.order.rapidata_order_configuration import (
    RapidataOrderConfiguration,
)
from src.service.rapidata_api_services.base_service import BaseRapidataAPIService


class OrderService(BaseRapidataAPIService):
    def __init__(self, client_id: str, client_secret: str, endpoint: str):
        super().__init__(
            client_id=client_id, client_secret=client_secret, endpoint=endpoint
        )

    def create_order(self, config: RapidataOrderConfiguration) -> tuple[str, str]:
        """
        order_name: name of the order that will be displayed in the Rapidata dashboard.
        question: The question shown to the labeler in the rapid.
        categories: The answer options, between which the labeler can choose.
        target_country_codes: A list of two digit target country codes.
        disable_translation: Per default, the question and categories get translated with DeepL (or Google Translate, if DeepL doesn't support a language). By setting this to `True`, the translation is disabled.
        referee: The referee determines when the task is done. See above for the options.
        """
        url = f"{self.endpoint}/Order/CreateDefaultOrder"

        feature_flags = [
            {"key": flag, "value": "true"} for flag in config.feature_flags
        ]

        if config.alert_on_fast_response > 0:
            feature_flags.append(
                {
                    "key": "alert_on_fast_response",
                    "value": str(config.alert_on_fast_response),
                }
            )

        if config.disable_translation:
            feature_flags.append({"key": "disable_translation", "value": "true"})

        payload = {
            "orderName": config.name,
            "datasetName": f"{config.name} dataset",
            "isPublic": False,
            "workflowConfig": config.workflow.to_dict(),
            "aggregatorType": "Classification",
        }

        response = self._post(url, json=payload)

        return response.json()["orderId"], response.json()["datasetId"]

    def submit(self, order_id: str):
        url = f"{self.endpoint}/Order/Submit"
        params = {"orderId": order_id}

        submit_response = self._post(url, params=params)

        return submit_response
    
    def approve(self, order_id: str):
        url = f"{self.endpoint}/Order/Approve"
        params = {"orderId": order_id}

        approve_response = self._post(url, params=params)

        return approve_response
