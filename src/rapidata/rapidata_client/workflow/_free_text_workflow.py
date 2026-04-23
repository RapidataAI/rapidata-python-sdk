from typing import Any
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_free_text_payload import (
    IRapidPayloadFreeTextPayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.api_client.models.i_order_workflow_input_model import (
    IOrderWorkflowInputModel,
)
from rapidata.api_client.models.i_order_workflow_input_model_simple_workflow_input_model import (
    IOrderWorkflowInputModelSimpleWorkflowInputModel,
)
from rapidata.api_client.models.i_rapid_blueprint import IRapidBlueprint
from rapidata.api_client.models.i_rapid_blueprint_free_text_rapid_blueprint import (
    IRapidBlueprintFreeTextRapidBlueprint,
)


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

    def _to_model(self) -> IOrderWorkflowInputModel:
        blueprint = IRapidBlueprintFreeTextRapidBlueprint(
            _t="FreeTextBlueprint",
            question=self._instruction,
            validationSystemPrompt=self._validation_system_prompt,
        )

        return IOrderWorkflowInputModel(
            actual_instance=IOrderWorkflowInputModelSimpleWorkflowInputModel(
                _t="SimpleWorkflow",
                blueprint=IRapidBlueprint(actual_instance=blueprint),
            )
        )

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        return IRapidPayload(
            actual_instance=IRapidPayloadFreeTextPayload(
                _t="FreeTextPayload",
                question=self._instruction,
            )
        )

    def __str__(self) -> str:
        return f"FreeTextWorkflow(instruction='{self._instruction}', validation_system_prompt={self._validation_system_prompt})"

    def __repr__(self) -> str:
        return f"FreeTextWorkflow(instruction={self._instruction!r}, validation_system_prompt={self._validation_system_prompt!r})"
