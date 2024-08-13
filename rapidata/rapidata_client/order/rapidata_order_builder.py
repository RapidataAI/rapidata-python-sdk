from rapidata.rapidata_client.workflow import Workflow
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.service import RapidataService


class RapidataOrderBuilder:
    """
    Builder object for creating Rapidata orders.

    Use the fluent interface to set the desired configuration. Add a workflow to the order using `.workflow()` and finally call `.create()` to create the order.

    :param rapidata_service: The RapidataService instance.
    :type rapidata_service: RapidataService
    :param name: The name of the order.
    :type name: str
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
        """
        Create a RapidataOrder instance based on the configured settings.

        :return: The created RapidataOrder instance.
        :rtype: RapidataOrder
        :raises ValueError: If no workflow is provided.
        """
        if self._workflow is None:
            raise ValueError("You must provide a blueprint to create an order.")

        return RapidataOrder(
            name=self._name, workflow=self._workflow, rapidata_service=self._rapidata_service
        ).create()

    def workflow(self, workflow: Workflow):
        """
        Set the workflow for the order.

        :param workflow: The workflow to be set.
        :type workflow: Workflow
        :return: The updated RapidataOrderBuilder instance.
        :rtype: RapidataOrderBuilder
        """
        self._workflow = workflow
        return self
