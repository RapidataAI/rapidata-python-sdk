from rapidata.api_client.models.simple_workflow_model import SimpleWorkflowModel
from rapidata.api_client.models.validation_set_zip_post_request_blueprint import (
    ValidationSetZipPostRequestBlueprint,
)
from rapidata.api_client.models.locate_rapid_blueprint import LocateRapidBlueprint
from rapidata.rapidata_client.workflow._base_workflow import Workflow
from rapidata.api_client import LocatePayload
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.api_client.models.rapid_modality import RapidModality


class LocateWorkflow(Workflow):
    modality = RapidModality.LOCATE

    def __init__(self, target: str):
        super().__init__(type="SimpleWorkflowConfig")
        self._target = target

    def _get_instruction(self) -> str:
        return self._target

    def _to_model(self) -> SimpleWorkflowModel:
        blueprint = LocateRapidBlueprint(_t="LocateBlueprint", target=self._target)

        return SimpleWorkflowModel(
            _t="SimpleWorkflow",
            blueprint=ValidationSetZipPostRequestBlueprint(blueprint),
        )

    def _to_payload(self, datapoint: Datapoint) -> LocatePayload:
        return LocatePayload(
            _t="LocatePayload",
            target=self._target,
        )

    def __str__(self) -> str:
        return f"LocateWorkflow(target='{self._target}')"

    def __repr__(self) -> str:
        return f"LocateWorkflow(target={self._target!r})"
