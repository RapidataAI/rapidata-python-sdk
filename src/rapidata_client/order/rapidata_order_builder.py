from src.rapidata_client.order.workflow.base_workflow import Workflow
from src.rapidata_client.order.rapidata_order import RapidataOrder
from src.rapidata_client.order.rapidata_order_configuration import (
    RapidataOrderConfiguration,
)
from src.service.rapidata_api_services.rapidata_service import RapidataService


class RapidataOrderBuilder:

    def __init__(
        self,
        rapidata_service: RapidataService,
        name: str,
    ):
        self._name = name
        self._alert_on_fast_response: int = 0
        self._disable_translation: bool = False
        self._feature_flags: list[str] = []
        self._target_country_codes: list[str] = []
        self._rapidata_service = rapidata_service
        self._workflow: Workflow | None = None

    def create(self) -> RapidataOrder:
        if self._workflow is None:
            raise ValueError("You must provide a blueprint to create an order.")

        config = RapidataOrderConfiguration(
            name=self._name,
            workflow=self._workflow,
            alert_on_fast_response=self._alert_on_fast_response,
            disable_translation=self._disable_translation,
            feature_flags=self._feature_flags,
            target_country_codes=self._target_country_codes,
        )

        return RapidataOrder(
            config=config, rapidata_service=self._rapidata_service
        ).create()
    
    def workflow(self, workflow: Workflow):
        self._workflow = workflow
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
