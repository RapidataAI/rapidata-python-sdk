from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.validation_set_zip_post_request_blueprint import (
    ValidationSetZipPostRequestBlueprint,
)
from rapidata.api_client.models.line_rapid_blueprint import LineRapidBlueprint
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client import LinePayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


class DrawWorkflow(Workflow):
    modality = RapidModality.LINE

    def __init__(self, target: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._target = target

    def _get_instruction(self) -> str:
        return self._target

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = LineRapidBlueprint(_t="LineBlueprint", target=self._target)

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=ValidationSetZipPostRequestBlueprint(blueprint),
        )

    def _to_payload(self, datapoint: Datapoint) -> LinePayload:
        return LinePayload(
            _t="LinePayload",
            target=self._target,
        )

    def __str__(self) -> str:
        return f"DrawWorkflow(target='{self._target}')"

    def __repr__(self) -> str:
        return f"DrawWorkflow(target={self._target!r})"
