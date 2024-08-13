from src.rapidata_client.order.dataset.rapidata_dataset import RapidataDataset
from src.rapidata_client.order.workflow.base_workflow import Workflow
from src.service.rapidata_api_services.rapidata_service import RapidataService


class RapidataOrder:

    def __init__(
        self, name: str, workflow: Workflow, rapidata_service: RapidataService
    ):
        self.name = name
        self.workflow = workflow
        self.rapidata_service = rapidata_service
        self.order_id = None
        self._dataset = None

    def create(self):
        self.order_id, dataset_id = self.rapidata_service.order.create_order(self.name, self.workflow.to_dict())
        self._dataset = RapidataDataset(dataset_id, self.rapidata_service)
        return self

    def submit(self):
        if self.order_id is None:
            raise ValueError("You must create the order before submitting it.")

        self.rapidata_service.order.submit(self.order_id)

    def approve(self):
        if self.order_id is None:
            raise ValueError("You must create the order before approving it.")

        self.rapidata_service.order.approve(self.order_id)

    @property
    def dataset(self):
        if self._dataset is None:
            raise ValueError("You must submit the order before accessing the dataset.")
        return self._dataset
