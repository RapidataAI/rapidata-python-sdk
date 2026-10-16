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
from rapidata.api_client.models.i_rapid_spec_classify_rapid_spec import (
    IRapidSpecClassifyRapidSpec,
)
from rapidata.api_client.models.options_binding import OptionsBinding
from rapidata.api_client.models.options_binding_option import OptionsBindingOption
from rapidata.rapidata_client.workflow._rapid_spec import (
    ASSET,
    literal,
    simple_workflow,
)


class ClassifyWorkflow(Workflow):
    """
    A workflow for classification tasks.

    This class represents a classification workflow where a question is presented
    along with a list of possible options for classification.

    Args:
        question (str): The classification question to be presented.
        options (list[str]): A list of possible classification options.

    Attributes:
        _question (str): The classification question.
        _options (list[str]): The list of classification options.
    """

    modality = RapidModality.CLASSIFY
    task_type = "Classification"

    def __init__(self, instruction: str, answer_options: list[str]):
        super().__init__(type="SimpleWorkflowConfig")
        self._validate_instruction(instruction)
        self._instruction = instruction
        self._answer_options = answer_options

    def _get_instruction(self) -> str:
        return self._instruction

    def _to_dict(self) -> dict[str, Any]:
        return {
            **super()._to_dict(),
            "rapid": {
                "_t": "Classify",
                "title": {"literal": self._instruction},
                "categories": {
                    "literal": [
                        {"label": option, "value": option}
                        for option in self._answer_options
                    ]
                },
            },
        }

    def _to_model(self) -> IOrderWorkflowInput:
        return simple_workflow(
            IRapidSpecClassifyRapidSpec(
                _t="Classify",
                asset=ASSET,
                title=literal(self._instruction),
                categories=OptionsBinding(
                    literal=[
                        OptionsBindingOption(label=option, value=option)
                        for option in self._answer_options
                    ]
                ),
            )
        )

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        return IRapidPayload(
            actual_instance=IRapidPayloadClassifyPayload(
                _t="ClassifyPayload",
                categories=[
                    ClassifyPayloadCategory(label=option, value=option)
                    for option in self._answer_options
                ],
                title=self._instruction,
            )
        )

    def __str__(self) -> str:
        return f"ClassifyWorkflow(instruction='{self._instruction}', options={self._answer_options})"

    def __repr__(self) -> str:
        return f"ClassifyWorkflow(instruction='{self._instruction}', answer_options={self._answer_options!r})"
