from rapidata.api_client.models.add_validation_rapid_model import IRapidPayload
from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_line_payload import (
    IRapidPayloadLinePayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality
from rapidata.api_client.models.i_rapid_spec_line_rapid_spec import (
    IRapidSpecLineRapidSpec,
)
from rapidata.rapidata_client.workflow._rapid_spec import (
    ASSET,
    literal,
    simple_workflow,
)


class DrawWorkflow(Workflow):
    modality = RapidModality.LINE
    task_type = "Draw"

    def __init__(self, target: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._validate_instruction(target)
        self._target = target

    def _get_instruction(self) -> str:
        return self._target

    def _to_model(self) -> IOrderWorkflowInput:
        return simple_workflow(
            IRapidSpecLineRapidSpec(
                _t="Line", asset=ASSET, target=literal(self._target)
            )
        )

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        return IRapidPayload(
            actual_instance=IRapidPayloadLinePayload(
                _t="LinePayload",
                target=self._target,
            )
        )

    def __str__(self) -> str:
        return f"DrawWorkflow(target='{self._target}')"

    def __repr__(self) -> str:
        return f"DrawWorkflow(target={self._target!r})"
