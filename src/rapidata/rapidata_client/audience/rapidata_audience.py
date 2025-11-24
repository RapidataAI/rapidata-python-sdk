from rapidata.rapidata_client.config import logger
from rapidata.rapidata_client.config import tracer
from rapidata.service.openapi_service import OpenAPIService
from rapidata.rapidata_client.filter import RapidataFilter
from rapidata.rapidata_client.validation.rapids.rapids import Rapid
from rapidata.rapidata_client.order.rapidata_order import RapidataOrder
from rapidata.rapidata_client.validation.validation_set_manager import (
    ValidationSetManager,
)
from rapidata.rapidata_client.order._rapidata_order_builder import RapidataOrderBuilder
from rapidata.rapidata_client.selection import (
    ValidationSelection,
    CappedSelection,
    LabelingSelection,
)
from rapidata.rapidata_client.datapoints._datapoint import Datapoint
from rapidata.rapidata_client.workflow import CompareWorkflow
from rapidata.rapidata_client.audience.audience_orders.audience_order import (
    AudienceOrder,
)
from rapidata.rapidata_client.audience.audience_orders.order_uploader import (
    OrderUploader,
)


class RapidataAudience:
    def __init__(
        self,
        id: str,
        name: str,
        filters: list[RapidataFilter],
        openapi_service: OpenAPIService,
    ):
        self.id = id
        self.name = name
        self.filters = filters
        self._validation_set_manager = ValidationSetManager(openapi_service)
        self._validation_set = self._validation_set_manager._create_validation_set(
            name=name + " Filtering Validation Set",
            dimensions=[self.id],
        )
        self._openapi_service = openapi_service
        self._order_uploader = OrderUploader(openapi_service)

    def update_filters(self, filters: list[RapidataFilter]) -> "RapidataAudience":
        # will update the filters for the audience as soon as endpoint is ready

        self.filters = filters
        return self

    def add_qualifying_rapid(self, rapid: Rapid) -> "RapidataAudience":
        with tracer.start_as_current_span("RapidataAudience.add_validation_rapid"):
            logger.debug(f"Adding validation rapid: {rapid} to audience: {self.id}")
            self._validation_set.add_rapid(rapid)
            return self

    def start_cooking(self) -> "RapidataAudience":
        # will start the cooking for the audience as soon as endpoint is ready
        with tracer.start_as_current_span("RapidataAudience.start_cooking"):
            logger.debug(f"Starting cooking for audience: {self.id}")
            # will start the cooking for the audience as soon as endpoint is ready
            order_builder = RapidataOrderBuilder(
                name=self.name + " Audience Order",
                openapi_service=self._openapi_service,
            )
            order_builder._datapoints(
                [Datapoint(asset="won't be shown", data_type="text")]
            )
            order_builder._workflow(CompareWorkflow(instruction="Won't be shown"))
            order_builder._filters(self.filters)
            order_builder._selections(
                [
                    CappedSelection(
                        selections=[
                            ValidationSelection(
                                validation_set_id=self._validation_set.id, amount=3
                            ),
                            LabelingSelection(amount=1),
                        ],
                        max_rapids=3,
                    )
                ]
            )
            order_builder._create()
            return self

    def assign_order(self, order: AudienceOrder) -> RapidataOrder:
        # will create the order for the audience as soon as endpoint is ready
        with tracer.start_as_current_span("RapidataAudience.assign_order"):
            logger.debug(f"Assigning order to audience: {self.id}")
            return self._order_uploader.upload_order(
                order, self.id, self._validation_set.id
            )

    def __str__(self) -> str:
        return (
            f"RapidataAudience(id={self.id}, name={self.name}, filters={self.filters})"
        )

    def __repr__(self) -> str:
        return self.__str__()
