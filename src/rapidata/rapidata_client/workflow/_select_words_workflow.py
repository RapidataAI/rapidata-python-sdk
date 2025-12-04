from rapidata.api_client.models.i_order_workflow_model import IOrderWorkflowModel
from rapidata.api_client.models.i_order_workflow_model_simple_workflow_model import (
    IOrderWorkflowModelSimpleWorkflowModel,
)
from rapidata.api_client.models.i_rapid_blueprint import IRapidBlueprint
from rapidata.api_client.models.i_rapid_blueprint_transcription_rapid_blueprint import (
    IRapidBlueprintTranscriptionRapidBlueprint,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_transcription_payload import (
    IRapidPayloadTranscriptionPayload,
)
from rapidata.api_client.models.transcription_word import TranscriptionWord
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.api_client.models.i_rapid_payload import IRapidPayload


class SelectWordsWorkflow(Workflow):
    """
    A workflow for select words tasks.

    This class represents a select words workflow
    where datapoints have a sentence attached to them where words can be selected.

    Attributes:
        _instruction (str): The instruction for the select words task.

    Args:
        instruction (str): The instruction to be provided for the select words task.
    """

    modality = RapidModality.TRANSCRIPTION

    def __init__(self, instruction: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._instruction = instruction

    def _get_instruction(self) -> str:
        return self._instruction

    def _to_model(self) -> IOrderWorkflowModel:
        blueprint = IRapidBlueprintTranscriptionRapidBlueprint(
            _t="TranscriptionBlueprint", title=self._instruction
        )

        return IOrderWorkflowModel(
            actual_instance=IOrderWorkflowModelSimpleWorkflowModel(
                _t="SimpleWorkflow",
                blueprint=IRapidBlueprint(actual_instance=blueprint),
            )
        )

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        assert (
            datapoint.sentence is not None
        ), "SelectWordsWorkflow requires a sentence datapoint"

        return IRapidPayload(
            actual_instance=IRapidPayloadTranscriptionPayload(
                _t="TranscriptionPayload",
                title=self._instruction,
                transcription=[
                    TranscriptionWord(word=word, wordIndex=i)
                    for i, word in enumerate(datapoint.sentence.split())
                ],
            )
        )

    def __str__(self) -> str:
        return f"SelectWordsWorkflow(instruction='{self._instruction}')"

    def __repr__(self) -> str:
        return f"SelectWordsWorkflow(instruction={self._instruction!r})"
