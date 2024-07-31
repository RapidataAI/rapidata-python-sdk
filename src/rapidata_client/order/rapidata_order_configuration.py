from dataclasses import dataclass

from src.rapidata_client.order.workflow.base_workflow import Workflow


@dataclass
class RapidataOrderConfiguration:
    name: str
    workflow: Workflow
    alert_on_fast_response: int
    disable_translation: bool
    feature_flags: list[str]
    target_country_codes: list[str]