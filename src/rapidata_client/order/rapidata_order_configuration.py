from dataclasses import dataclass

from src.rapidata_client.order.referee.referee_interface import Referee


@dataclass
class RapidataOrderConfiguration:
    name: str
    question: str
    categories: list[str]
    alert_on_fast_response: int
    disable_translation: bool
    feature_flags: list[str]
    target_country_codes: list[str]
    referee: Referee