from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.simple_workflow_model_blueprint import (
    SimpleWorkflowModelBlueprint,
)
from rapidata.api_client.models.transcription_rapid_blueprint import (
    TranscriptionRapidBlueprint,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client import TranscriptionPayload, TranscriptionWord
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


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

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = TranscriptionRapidBlueprint(
            _t="TranscriptionBlueprint", title=self._instruction
        )

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=SimpleWorkflowModelBlueprint(blueprint),
        )

    def _to_payload(self, datapoint: Datapoint) -> TranscriptionPayload:
        assert (
            datapoint.sentence is not None
        ), "SelectWordsWorkflow requires a sentence datapoint"

        return TranscriptionPayload(
            _t="TranscriptionPayload",
            title=self._instruction,
            transcription=[
                TranscriptionWord(word=word, wordIndex=i)
                for i, word in enumerate(datapoint.sentence.split())
            ],
        )

    def __str__(self) -> str:
        return f"SelectWordsWorkflow(instruction='{self._instruction}')"

    def __repr__(self) -> str:
        return f"SelectWordsWorkflow(instruction={self._instruction!r})"
