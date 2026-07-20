from rapidata.api_client.models.i_order_workflow_input import (
    IOrderWorkflowInput,
)
from rapidata.api_client.models.i_order_workflow_input_simple_workflow_input import (
    IOrderWorkflowInputSimpleWorkflowInput,
)
from rapidata.api_client.models.i_rapid_blueprint import IRapidBlueprint
from rapidata.api_client.models.i_rapid_blueprint_locate_rapid_blueprint import (
    IRapidBlueprintLocateRapidBlueprint,
)
from rapidata.api_client.models.i_rapid_payload import IRapidPayload
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_locate_payload import (
    IRapidPayloadLocatePayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


class LocateWorkflow(Workflow):
    modality = RapidModality.LOCATE
    task_type = "Locate"

    def __init__(self, target: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._validate_instruction(target)
        self._target = target

    def _get_instruction(self) -> str:
        return self._target

    def _to_model(self) -> IOrderWorkflowInput:
        blueprint = IRapidBlueprintLocateRapidBlueprint(
            _t="LocateBlueprint", target=self._target
        )

        return IOrderWorkflowInput(
            actual_instance=IOrderWorkflowInputSimpleWorkflowInput(
                _t="SimpleWorkflow",
                blueprint=IRapidBlueprint(actual_instance=blueprint),
            )
        )

    def _to_payload(self, datapoint: Datapoint) -> IRapidPayload:
        return IRapidPayload(
            actual_instance=IRapidPayloadLocatePayload(
                _t="LocatePayload",
                target=self._target,
            )
        )

    def __str__(self) -> str:
        return f"LocateWorkflow(target='{self._target}')"

    def __repr__(self) -> str:
        return f"LocateWorkflow(target={self._target!r})"
