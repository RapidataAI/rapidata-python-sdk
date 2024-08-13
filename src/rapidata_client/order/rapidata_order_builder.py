from src.rapidata_client.order.workflow.base_workflow import Workflow
from src.rapidata_client.order.rapidata_order import RapidataOrder
from src.service.rapidata_api_services.rapidata_service import RapidataService


class RapidataOrderBuilder:
    """
    Builder object for creating Rapidata orders. Use the fluent interface to set the desired configuration. Add a workflow to the order using .workflow() and finally call .create() to create the order.
    """

    def __init__(
        self,
        rapidata_service: RapidataService,
        name: str,
    ):
        self._name = name
        self._rapidata_service = rapidata_service
        self._workflow: Workflow | None = None

    def create(self) -> RapidataOrder:
        if self._workflow is None:
            raise ValueError("You must provide a blueprint to create an order.")

        return RapidataOrder(
            name=self._name, workflow=self._workflow, rapidata_service=self._rapidata_service
        ).create()

    def workflow(self, workflow: Workflow):
        self._workflow = workflow
        return self
