from typing import Any
from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.validation_set_zip_post_request_blueprint import (
    ValidationSetZipPostRequestBlueprint,
)
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client.models.free_text_rapid_blueprint import FreeTextRapidBlueprint
from rapidata.api_client import FreeTextPayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


class FreeTextWorkflow(Workflow):
    """
    A workflow for free text input tasks.

    This class represents a workflow where users can provide free-form text responses
    to a given instruction.

    Attributes:
        _instruction (str): The instruction to be answered with free text.

    Args:
        instruction (str): The instruction to be presented for free text input.
        validation_system_prompt (str): The system prompt to determine if the provided free text response is spam or not.
            Should always specify that the LLM should respond with 'not spam' or 'spam'.
    """

    modality = RapidModality.FREETEXT

    def __init__(self, instruction: str, validation_system_prompt: str | None = None):
        super().__init__(type="SimpleWorkflowConfig")
        self._instruction = instruction
        self._validation_system_prompt = validation_system_prompt

    def _get_instruction(self) -> str:
        return self._instruction

    def _to_dict(self) -> dict[str, Any]:
        return {
            **super()._to_dict(),
            "blueprint": {
                "_t": "FreeTextBlueprint",
                "question": self._instruction,
                "validationSystemPrompt": self._validation_system_prompt,
            },
        }

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = FreeTextRapidBlueprint(
            _t="FreeTextBlueprint",
            question=self._instruction,
            validationSystemPrompt=self._validation_system_prompt,
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=ValidationSetZipPostRequestBlueprint(blueprint),
        )

    def _to_payload(self, datapoint: Datapoint) -> FreeTextPayload:
        return FreeTextPayload(
            _t="FreeTextPayload",
            question=self._instruction,
        )

    def __str__(self) -> str:
        return f"FreeTextWorkflow(instruction='{self._instruction}', validation_system_prompt={self._validation_system_prompt})"

    def __repr__(self) -> str:
        return f"FreeTextWorkflow(instruction={self._instruction!r}, validation_system_prompt={self._validation_system_prompt!r})"
