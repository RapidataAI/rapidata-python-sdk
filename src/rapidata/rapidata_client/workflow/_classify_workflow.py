from typing import Any
from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.rapidata_client.workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_classify_payload import (
    IRapidPayloadClassifyPayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.api_client.models.classify_payload_category import ClassifyPayloadCategory
from rapidata.rapidata_client.datapoints._default_segments import (
    ANSWER_OPTIONS_SEGMENT_KEY,
)
from rapidata.api_client.models.i_rapid_spec_classify_rapid_spec import (
    IRapidSpecClassifyRapidSpec,
)
from rapidata.api_client.models.options_binding import OptionsBinding
from rapidata.rapidata_client.workflow._rapid_spec import (
    ASSET,
    literal,
    simple_workflow,
)


class ClassifyWorkflow(Workflow):
    """
    A workflow for classification tasks.

    The question is the same for every datapoint; the answer options are read
    from each datapoint's ``answer_options``.

    Args:
        instruction (str): The classification question to be presented.
    """

    modality = RapidModality.CLASSIFY
    task_type = "Classification"

    def __init__(self, instruction: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._validate_instruction(instruction)
        self._instruction = instruction

    def _get_instruction(self) -> str:
        return self._instruction

    def _required_segments(self) -> set[str]:
        return {ANSWER_OPTIONS_SEGMENT_KEY}

    def _to_dict(self) -> dict[str, Any]:
        return {
            **super()._to_dict(),
            "rapid": {
                "_t": "Classify",
                "title": {"literal": self._instruction},
                "categories": {"segment": ANSWER_OPTIONS_SEGMENT_KEY},
            },
        }

    def _to_model(self) -> IOrderWorkflowInput:
        return simple_workflow(
            IRapidSpecClassifyRapidSpec(
                _t="Classify",
                asset=ASSET,
                title=literal(self._instruction),
                categories=OptionsBinding(segment=ANSWER_OPTIONS_SEGMENT_KEY),
            )
        )

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        return IRapidPayload(
            actual_instance=IRapidPayloadClassifyPayload(
                _t="ClassifyPayload",
                categories=[
                    ClassifyPayloadCategory(label=option, value=option)
                    for option in datapoint.answer_options or []
                ],
                title=self._instruction,
            )
        )

    def __str__(self) -> str:
        return f"ClassifyWorkflow(instruction='{self._instruction}')"

    def __repr__(self) -> str:
        return f"ClassifyWorkflow(instruction='{self._instruction}')"
