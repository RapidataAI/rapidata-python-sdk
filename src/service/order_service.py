import requests

from src.rapidata_client.order.rapidata_order_configuration import RapidataOrderConfiguration


class OrderService:
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.auth_header = {"Authorization": f"Bearer {api_key}"}

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

        feature_flags = [{"key": flag, "value": "true"} for flag in config.feature_flags]

        if config.alert_on_fast_response > 0:
            feature_flags.append(
                {"key": "alert_on_fast_response", "value": str(config.alert_on_fast_response)}
            )

        if config.disable_translation:
            feature_flags.append({"key": "disable_translation", "value": "true"})

        payload = {
            "orderName": config.name,
            "datasetName": f"{config.name} dataset",
            "isPublic": False,
            "workflowConfig": {
                "_t": "SimpleWorkflowConfig",
                "featureFlags": feature_flags,
                "targetCountryCodes": config.target_country_codes,
                "referee": config.referee.to_dict(),
                "isFallback": False,
                "rapidSelectionConfigs": [],
                "blueprint": {
                    "_t": "AttachCategoryRapidBlueprint",
                    "possibleCategories": config.categories,
                    "title": config.question,
                },
            },
            "aggregatorType": "Classification",
        }

        response = requests.post(url, json=payload, headers=self.auth_header)
        self._check_response(response)

        return response.json()["orderId"], response.json()["datasetId"]
    
    def submit(self, order_id):
        url = f"{self.endpoint}/Order/Submit"
        params = {"orderId": order_id}

        submit_response = requests.post(
            url, params=params, headers=self.auth_header
        )
        self._check_response(submit_response)

        return submit_response
    
    def _check_response(self, response):
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} - {response.text}")