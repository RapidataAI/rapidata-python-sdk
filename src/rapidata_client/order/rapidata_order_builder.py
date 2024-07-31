from src.rapidata_client.order.rapidata_order import RapidataOrder
from src.rapidata_client.order.rapidata_order_configuration import RapidataOrderConfiguration
from src.rapidata_client.order.referee.abstract_referee import Referee
from src.rapidata_client.order.referee.naive_referee import NaiveReferee
from src.service.rapidata_api_services.rapidata_service import RapidataService


class RapidataOrderBuilder:

    def __init__(
        self,
        rapidata_service: RapidataService,
        name: str,
        question: str,
        categories: list[str],
    ):
        self._name = name
        self._question = question
        self._categories = categories
        self._alert_on_fast_response: int = 0
        self._disable_translation: bool = False
        self._feature_flags: list[str] = []
        self._target_country_codes: list[str] = []
        self._referee: Referee = NaiveReferee()
        self._rapidata_service = rapidata_service

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

        return RapidataOrder(
            config=config, rapidata_service=self._rapidata_service
        ).create()

    def referee(self, referee: Referee):
        self._referee = referee
        return self

    def target_country_codes(self, target_country_codes: list[str]):
        self._target_country_codes = target_country_codes
        return self

    def feature_flags(self, feature_flags: list[str]):
        self._feature_flags = feature_flags
        return self

    def disable_translation(self, disable_translation: bool):
        self._disable_translation = disable_translation
        return self

    def alert_on_fast_response(self, alert_on_fast_response: int):
        self._alert_on_fast_response = alert_on_fast_response
        return self
