from rapidata.api_client.models.add_validation_rapid_model import IRapidPayload
from rapidata.api_client.models.i_order_workflow_model import IOrderWorkflowModel
from rapidata.api_client.models.i_order_workflow_model_simple_workflow_model import (
    IOrderWorkflowModelSimpleWorkflowModel,
)
from rapidata.api_client.models.i_rapid_blueprint import IRapidBlueprint
from rapidata.api_client.models.i_rapid_blueprint_line_rapid_blueprint import (
    IRapidBlueprintLineRapidBlueprint,
)
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client.models.i_rapid_payload_line_payload import (
    IRapidPayloadLinePayload,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


class DrawWorkflow(Workflow):
    modality = RapidModality.LINE

    def __init__(self, target: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._target = target

    def _get_instruction(self) -> str:
        return self._target

    def _to_model(self) -> IOrderWorkflowModel:
        blueprint = IRapidBlueprintLineRapidBlueprint(
            _t="LineBlueprint", target=self._target
        )

        return IOrderWorkflowModel(
            actual_instance=IOrderWorkflowModelSimpleWorkflowModel(
                _t="SimpleWorkflow",
                blueprint=IRapidBlueprint(actual_instance=blueprint),
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
