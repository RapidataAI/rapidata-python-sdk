from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_transcription_payload import (
    IRapidPayloadTranscriptionPayload,
)
from rapidata.api_client.models.transcription_payload_transcription_word import (
    TranscriptionPayloadTranscriptionWord,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.api_client.models.i_rapid_spec_transcription_rapid_spec import (
    IRapidSpecTranscriptionRapidSpec,
)
from rapidata.rapidata_client.workflow._rapid_spec import (
    ASSET,
    literal,
    segment,
    simple_workflow,
)
from rapidata.rapidata_client.datapoints._default_segments import (
    TRANSCRIPTION_SEGMENT_KEY,
)


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
    task_type = "Select Words"

    def __init__(self, instruction: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._validate_instruction(instruction)
        self._instruction = instruction

    def _get_instruction(self) -> str:
        return self._instruction

    def _to_model(self) -> IOrderWorkflowInput:
        return simple_workflow(
            IRapidSpecTranscriptionRapidSpec(
                _t="Transcription",
                asset=ASSET,
                title=literal(self._instruction),
                transcription=segment(TRANSCRIPTION_SEGMENT_KEY),
            )
        )

    def _required_segments(self) -> set[str]:
        return {TRANSCRIPTION_SEGMENT_KEY}

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        assert (
            datapoint.sentence is not None
        ), "SelectWordsWorkflow requires a sentence datapoint"

        return IRapidPayload(
            actual_instance=IRapidPayloadTranscriptionPayload(
                _t="TranscriptionPayload",
                title=self._instruction,
                transcription=[
                    TranscriptionPayloadTranscriptionWord(word=word, wordIndex=i)
                    for i, word in enumerate(datapoint.sentence.split())
                ],
            )
        )

    def __str__(self) -> str:
        return f"SelectWordsWorkflow(instruction='{self._instruction}')"

    def __repr__(self) -> str:
        return f"SelectWordsWorkflow(instruction={self._instruction!r})"
