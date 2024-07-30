from src.rapidata_client.order.rapidata_order import RapidataOrder
from src.rapidata_client.order.rapidata_order_configuration import RapidataOrderConfiguration
from src.rapidata_client.order.referee.naive_referee import NaiveReferee
from src.service.order_service import OrderService


class RapidataOrderBuilder:

    def __init__(self, order_service: OrderService, name: str, question: str, categories: list[str]):
        self._name = name
        self._question = question
        self._categories = categories
        self._alert_on_fast_response = 0
        self._disable_translation = False
        self._feature_flags = []
        self._target_country_codes = []
        self._referee = NaiveReferee()
        self._order_service = order_service

    def create(self) -> RapidataOrder:
        config = RapidataOrderConfiguration(
            name=self._name,
            question=self._question,
            categories=self._categories,
            alert_on_fast_response=self._alert_on_fast_response,
            disable_translation=self._disable_translation,
            feature_flags=self._feature_flags,
            target_country_codes=self._target_country_codes,
            referee=self._referee,
        )

        return RapidataOrder(config=config, order_service=self._order_service)

    def referee(self, referee):
        self._referee = referee
        return self

    def target_country_codes(self, target_country_codes):
        self._target_country_codes = target_country_codes
        return self

    def feature_flags(self, feature_flags):
        self._feature_flags = feature_flags
        return self

    def disable_translation(self, disable_translation):
        self._disable_translation = disable_translation
        return self

    def alert_on_fast_response(self, alert_on_fast_response):
        self._alert_on_fast_response = alert_on_fast_response
        return self
